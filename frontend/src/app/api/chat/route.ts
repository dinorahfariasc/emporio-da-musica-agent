import { auth } from "../../../../auth";
import { backendUrl } from "@/lib/backend";
import { findUserById } from "@/lib/auth/db";
import { mintServiceJwt } from "@/lib/auth/service-jwt";
import { mockChatResponse } from "@/lib/chat/mock";
import { chatMode } from "@/lib/chat/mode";

const UNAUTHORIZED_BODY = {
  error: {
    code: "unauthorized",
    message: "Sua sessão expirou. Entre novamente para continuar.",
  },
};

// Only these are meaningful to forward: the SSE contract headers and content-type for an error
// JSON body. content-length/content-encoding/transfer-encoding are dropped deliberately — Node's
// fetch may already have decoded/rechunked the body, so forwarding those verbatim can desync the
// client from the actual bytes sent.
const FORWARDED_RESPONSE_HEADERS = [
  "content-type",
  "x-vercel-ai-ui-message-stream",
  "cache-control",
  "x-accel-buffering",
  "retry-after",
];

function unauthorized(): Response {
  return Response.json(UNAUTHORIZED_BODY, { status: 401 });
}

function forwardedHeaders(upstream: Headers): Headers {
  const headers = new Headers();
  for (const name of FORWARDED_RESPONSE_HEADERS) {
    const value = upstream.get(name);
    if (value !== null) headers.set(name, value);
  }
  return headers;
}

// Mode is chosen by chatMode() (fails closed to the backend in production, regardless of
// CHAT_MODE — see chatMode's own doc comment).
export async function POST(request: Request) {
  if (chatMode(process.env) === "mock") {
    return mockChatResponse(await request.json());
  }

  const session = await auth();
  if (!session?.user?.id) {
    return unauthorized();
  }

  // Re-check disabled status at mint time, not only at login (data-model.md note on US1), keyed
  // by the session's account id rather than its display name.
  const user = await findUserById(session.user.id);
  if (!user || user.disabledAt) {
    return unauthorized();
  }

  const secret = process.env.SERVICE_JWT_SECRET;
  if (!secret) {
    return Response.json(
      { error: { code: "internal_error", message: "server misconfigured" } },
      { status: 500 },
    );
  }

  // Parsed only after auth succeeds: an unauthenticated/disabled caller's body is never touched.
  const body = await request.json();

  let token: string;
  try {
    token = await mintServiceJwt(user.id, user.username, secret);
  } catch {
    return Response.json(
      { error: { code: "internal_error", message: "server misconfigured" } },
      { status: 500 },
    );
  }

  const upstream = await fetch(backendUrl("/api/chat"), {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
    // A client abort (e.g. navigating away mid-stream) cancels the upstream backend turn instead
    // of leaving it running to completion for nobody.
    signal: request.signal,
  });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: forwardedHeaders(upstream.headers),
  });
}
