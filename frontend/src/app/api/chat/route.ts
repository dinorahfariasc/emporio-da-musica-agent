import { backendUrl } from "@/lib/backend";
import { mockChatResponse } from "@/lib/chat/mock";
import { chatMode } from "@/lib/chat/mode";

// Mode is chosen by chatMode() (fails closed to the backend in production). Auth is added in #10.
export async function POST(request: Request) {
  const body = await request.json();

  if (chatMode(process.env) === "mock") {
    return mockChatResponse(body);
  }

  const upstream = await fetch(backendUrl("/api/chat"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return new Response(upstream.body, { status: upstream.status, headers: upstream.headers });
}
