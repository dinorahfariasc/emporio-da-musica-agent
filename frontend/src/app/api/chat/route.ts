import { backendUrl } from "@/lib/backend";
import { mockChatResponse } from "@/lib/chat/mock";

// CHAT_MODE=mock replays contract fixtures (default for local UI work);
// CHAT_MODE=backend proxies to the FastAPI agent. Auth is added in #10.
export async function POST(request: Request) {
  const body = await request.json();

  if ((process.env.CHAT_MODE ?? "mock") === "mock") {
    return mockChatResponse(body);
  }

  const upstream = await fetch(backendUrl("/api/chat"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return new Response(upstream.body, { status: upstream.status, headers: upstream.headers });
}
