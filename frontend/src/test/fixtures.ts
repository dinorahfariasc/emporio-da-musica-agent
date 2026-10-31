import { readFileSync } from "node:fs";
import path from "node:path";

import {
  parseJsonEventStream,
  readUIMessageStream,
  uiMessageChunkSchema,
  type UIMessageChunk,
} from "ai";

import type { ChatMessage } from "@/lib/chat/types";

// Shared contract fixtures (#4): the single source for contract, rendering and flow tests.
export const FIXTURES_DIR = path.resolve(__dirname, "../../../contracts/chat-stream/fixtures");

const STREAM_HEADERS = {
  "Content-Type": "text/event-stream",
  "x-vercel-ai-ui-message-stream": "v1",
};

function fileName(name: string): string {
  return path.extname(name) ? name : `${name}${name.startsWith("http-") ? ".json" : ".sse"}`;
}

export function readFixture(name: string): string {
  return readFileSync(path.join(FIXTURES_DIR, fileName(name)), "utf8");
}

export async function parseChunks(name: string): Promise<UIMessageChunk[]> {
  const parsed = parseJsonEventStream({
    stream: new Response(readFixture(name)).body!,
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

export async function assembleMessage(name: string): Promise<ChatMessage> {
  const chunks = await parseChunks(name);
  const stream = new ReadableStream<UIMessageChunk>({
    start(controller) {
      chunks.forEach((c) => controller.enqueue(c));
      controller.close();
    },
  });
  let last: ChatMessage | undefined;
  for await (const message of readUIMessageStream<ChatMessage>({ stream, onError: () => {} })) {
    last = message;
  }
  return last!;
}

export type HttpFixture = {
  status: number;
  headers: Record<string, string>;
  body: { error: { code: string; message: string; retryAfterSeconds?: number } };
};

export function readHttpFixture(name: string): HttpFixture {
  return JSON.parse(readFixture(name));
}

type FixtureFetchOptions = {
  /** Drop the `finish` chunk and `[DONE]`, like a connection that closes early. */
  truncate?: boolean;
  /** Send this many events, then hold the stream open until the request is aborted. */
  pauseAfter?: number;
};

export type FixtureFetch = typeof fetch & { requests: Record<string, unknown>[] };

/**
 * A `fetch` stub for `DefaultChatTransport` that answers with fixtures. An array serves the
 * names in order (the last one repeats). Request bodies are recorded in `requests`.
 */
export function fixtureFetch(
  names: string | string[],
  { truncate = false, pauseAfter }: FixtureFetchOptions = {},
): FixtureFetch {
  const queue = Array.isArray(names) ? names : [names];
  const requests: Record<string, unknown>[] = [];

  const stub = async (_input: RequestInfo | URL, init?: RequestInit) => {
    requests.push(JSON.parse(String(init?.body ?? "{}")));
    const name = queue[Math.min(requests.length - 1, queue.length - 1)];

    if (name.startsWith("http-")) {
      const spec = readHttpFixture(name);
      return Response.json(spec.body, { status: spec.status, headers: spec.headers });
    }

    let events = readFixture(name).split("\n\n").filter(Boolean);
    if (truncate) {
      events = events.filter((e) => !e.includes('"type":"finish"') && !e.includes("[DONE]"));
    }
    const encoder = new TextEncoder();
    const signal = init?.signal;
    const body = new ReadableStream<Uint8Array>({
      async start(controller) {
        for (const [i, event] of events.entries()) {
          if (pauseAfter !== undefined && i === pauseAfter) {
            await new Promise<void>((resolve) => {
              if (signal?.aborted) return resolve();
              signal?.addEventListener("abort", () => resolve(), { once: true });
            });
            controller.error(new DOMException("The operation was aborted.", "AbortError"));
            return;
          }
          controller.enqueue(encoder.encode(`${event}\n\n`));
          await new Promise((resolve) => setTimeout(resolve, 0));
        }
        controller.close();
      },
    });
    return new Response(body, { headers: STREAM_HEADERS });
  };

  return Object.assign(stub, { requests }) as FixtureFetch;
}
