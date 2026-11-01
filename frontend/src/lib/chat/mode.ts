export type ChatMode = "mock" | "backend";

type Env = { CHAT_MODE?: string; NODE_ENV?: string };

// CHAT_MODE=mock replays contract fixtures; CHAT_MODE=backend proxies to the agent.
// Mock mode skips auth and the service JWT entirely (route.ts returns it before checking the
// session), so production ALWAYS uses the backend regardless of CHAT_MODE — a misconfigured env
// var must not be able to open the public URL back up to unauthenticated fixture replay.
export function chatMode(env: Env): ChatMode {
  if (env.NODE_ENV === "production") return "backend";
  const mode = env.CHAT_MODE ?? "mock";
  return mode === "mock" ? "mock" : "backend";
}
