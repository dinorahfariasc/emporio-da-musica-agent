import { connection } from "next/server";

import { backendUrl } from "@/lib/backend";

export async function GET() {
  await connection();
  try {
    const upstream = await fetch(backendUrl("/api/health"), { cache: "no-store" });
    return Response.json(await upstream.json(), { status: upstream.status });
  } catch (error) {
    console.error("Backend health check failed", error);
    return Response.json({ status: "degraded", backend: "unreachable" }, { status: 502 });
  }
}
