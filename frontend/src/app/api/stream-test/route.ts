import { connection } from "next/server";

import { backendUrl } from "@/lib/backend";

// Walking skeleton: proves SSE flows browser → Next.js → FastAPI without buffering.
export async function GET() {
  await connection();
  const upstream = await fetch(backendUrl("/api/stream-test"), { cache: "no-store" });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
