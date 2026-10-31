export type ChatMode = "mock" | "backend";

type Env = { CHAT_MODE?: string; NODE_ENV?: string };

// CHAT_MODE=mock replays contract fixtures; CHAT_MODE=backend proxies to the agent.
// Unset in production fails closed to the backend so the public URL never serves fixtures.
export function chatMode(env: Env): ChatMode {
  const mode = env.CHAT_MODE ?? (env.NODE_ENV === "production" ? "backend" : "mock");
  return mode === "mock" ? "mock" : "backend";
}
