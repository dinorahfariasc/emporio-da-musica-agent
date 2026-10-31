import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";

import {
  parseJsonEventStream,
  readUIMessageStream,
  uiMessageChunkSchema,
  type UIMessage,
  type UIMessageChunk,
} from "ai";
import { describe, expect, it } from "vitest";

const FIXTURES = path.resolve(__dirname, "../../../../contracts/chat-stream/fixtures");
const sseFixtures = readdirSync(FIXTURES).filter((f) => f.endsWith(".sse"));

function toStream(text: string): ReadableStream<Uint8Array> {
  return new Response(text).body!;
}

async function parseChunks(name: string): Promise<UIMessageChunk[]> {
  const parsed = parseJsonEventStream({
    stream: toStream(readFileSync(path.join(FIXTURES, name), "utf8")),
    schema: uiMessageChunkSchema,
  });
  const chunks: UIMessageChunk[] = [];
  const reader = parsed.getReader();
  for (let read = await reader.read(); !read.done; read = await reader.read()) {
    if (!read.value.success) throw read.value.error;
    chunks.push(read.value.value as UIMessageChunk);
  }
  return chunks;
}

async function finalMessage(chunks: UIMessageChunk[]): Promise<UIMessage> {
  const stream = new ReadableStream<UIMessageChunk>({
    start(controller) {
      chunks.forEach((c) => controller.enqueue(c));
      controller.close();
    },
  });
  let last: UIMessage | undefined;
  for await (const message of readUIMessageStream({
    stream,
    onError: () => {},
  })) {
    last = message;
  }
  return last!;
}

describe("chat stream contract fixtures", () => {
  it("has the expected fixtures", () => {
    expect(sseFixtures.sort()).toEqual([
      "plain-text.sse",
      "stream-error.sse",
      "tool-error.sse",
      "tool-products.sse",
    ]);
  });

  it.each(sseFixtures)("%s is valid against the AI SDK chunk schema", async (name) => {
    const chunks = await parseChunks(name);
    expect(chunks[0]).toMatchObject({ type: "start" });
  });

  it("plain-text assembles into one text part with route metadata", async () => {
    const message = await finalMessage(await parseChunks("plain-text.sse"));
    const text = message.parts.filter((p) => p.type === "text");
    expect(text).toHaveLength(1);
    expect(message.metadata).toMatchObject({ route: { intent: "greeting" } });
  });

  it("tool-products exposes the tool call and the products data part", async () => {
    const message = await finalMessage(await parseChunks("tool-products.sse"));
    const tool = message.parts.find((p) => p.type === "tool-search_products");
    expect(tool).toMatchObject({ state: "output-available" });
    const data = message.parts.find((p) => p.type === "data-products");
    expect(data).toMatchObject({ data: { products: [{ id: 91 }, { id: 87 }] } });
  });

  it("tool-error surfaces a tool part in error state", async () => {
    const message = await finalMessage(await parseChunks("tool-error.sse"));
    const tool = message.parts.find((p) => p.type === "tool-get_order_status");
    expect(tool).toMatchObject({ state: "output-error", errorText: "verification_failed" });
  });

  it("stream-error ends with an error chunk", async () => {
    const chunks = await parseChunks("stream-error.sse");
    expect(chunks.at(-1)).toMatchObject({ type: "error" });
  });
});
