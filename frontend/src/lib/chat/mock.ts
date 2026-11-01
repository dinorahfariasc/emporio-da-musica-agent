import { readFile } from "node:fs/promises";
import path from "node:path";

// Dev-only mock that replays the shared contract fixtures (contracts/chat-stream/fixtures).
// Pick a fixture by sending "/fixture <name>", e.g. "/fixture tool-products" or "/fixture http-401".
const FIXTURES_DIR = path.join(process.cwd(), "..", "contracts", "chat-stream", "fixtures");
const DEFAULT_FIXTURE = "plain-text";
const CHUNK_DELAY_MS = 40;

const STREAM_HEADERS = {
  "Content-Type": "text/event-stream",
  "Cache-Control": "no-cache",
  "x-vercel-ai-ui-message-stream": "v1",
};

type ChatBody = {
  messages?: { role: string; parts?: { type: string; text?: string }[] }[];
};

export function pickFixture(body: ChatBody): string {
  const lastUser = body.messages?.filter((m) => m.role === "user").at(-1);
  const text = lastUser?.parts?.find((p) => p.type === "text")?.text ?? "";
  const match = text.match(/\/fixture\s+([a-z0-9-]+)/i);
  return match?.[1] ?? DEFAULT_FIXTURE;
}

export async function mockChatResponse(body: ChatBody): Promise<Response> {
  const name = pickFixture(body);

  if (name.startsWith("http-")) {
    const spec = JSON.parse(await readFile(path.join(FIXTURES_DIR, `${name}.json`), "utf8"));
    return Response.json(spec.body, { status: spec.status, headers: spec.headers });
  }

  // Fixtures carry a fixed messageId; a real backend sends a new one per answer.
  const messageId = `msg_mock_${crypto.randomUUID()}`;
  const events = (await readFile(path.join(FIXTURES_DIR, `${name}.sse`), "utf8"))
    .replace(/"messageId":"[^"]*"/, `"messageId":"${messageId}"`)
    .split("\n\n")
    .filter(Boolean);
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      for (const event of events) {
        controller.enqueue(encoder.encode(`${event}\n\n`));
        await new Promise((resolve) => setTimeout(resolve, CHUNK_DELAY_MS));
      }
      controller.close();
    },
  });
  return new Response(stream, { headers: STREAM_HEADERS });
}
