import { readdirSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { assembleMessage, FIXTURES_DIR, parseChunks } from "@/test/fixtures";

const sseFixtures = readdirSync(FIXTURES_DIR).filter((f) => f.endsWith(".sse"));

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
    const message = await assembleMessage("plain-text.sse");
    const text = message.parts.filter((p) => p.type === "text");
    expect(text).toHaveLength(1);
    expect(message.metadata).toMatchObject({ route: { intent: "greeting" } });
  });

  it("tool-products exposes the tool call and the products data part", async () => {
    const message = await assembleMessage("tool-products.sse");
    const tool = message.parts.find((p) => p.type === "tool-search_products");
    expect(tool).toMatchObject({ state: "output-available" });
    const data = message.parts.find((p) => p.type === "data-products");
    expect(data).toMatchObject({ data: { products: [{ id: 91 }, { id: 87 }] } });
  });

  it("tool-error surfaces a tool part in error state", async () => {
    const message = await assembleMessage("tool-error.sse");
    const tool = message.parts.find((p) => p.type === "tool-get_order_status");
    expect(tool).toMatchObject({ state: "output-error", errorText: "verification_failed" });
  });

  it("stream-error ends with an error chunk", async () => {
    const chunks = await parseChunks("stream-error.sse");
    expect(chunks.at(-1)).toMatchObject({ type: "error" });
  });
});
