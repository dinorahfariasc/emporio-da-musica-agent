import { auth } from "../../../../auth";
import { backendUrl } from "@/lib/backend";
import { findUserByUsername } from "@/lib/auth/db";
import { mintServiceJwt } from "@/lib/auth/service-jwt";
import { mockChatResponse } from "@/lib/chat/mock";
import { chatMode } from "@/lib/chat/mode";

const UNAUTHORIZED_BODY = {
  error: {
    code: "unauthorized",
    message: "Sua sessão expirou. Entre novamente para continuar.",
  },
};

function unauthorized(): Response {
  return Response.json(UNAUTHORIZED_BODY, { status: 401 });
}

// Mode is chosen by chatMode() (fails closed to the backend in production).
export async function POST(request: Request) {
  const body = await request.json();

  if (chatMode(process.env) === "mock") {
    return mockChatResponse(body);
  }

  const session = await auth();
  if (!session?.user?.id || !session.user.name) {
    return unauthorized();
  }

  // Re-check disabled status at mint time, not only at login (data-model.md note on US1).
  const user = await findUserByUsername(session.user.name);
  if (!user || user.disabledAt) {
    return unauthorized();
  }

  const secret = process.env.SERVICE_JWT_SECRET;
  if (!secret) {
    return Response.json({ error: { code: "internal_error", message: "server misconfigured" } }, {
      status: 500,
    });
  }
  const token = await mintServiceJwt(session.user.id, session.user.name, secret);

  const upstream = await fetch(backendUrl("/api/chat"), {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });
  return new Response(upstream.body, { status: upstream.status, headers: upstream.headers });
}
