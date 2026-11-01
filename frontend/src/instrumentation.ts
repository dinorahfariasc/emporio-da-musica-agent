// Next.js instrumentation hook: register() runs once when the server process starts (both `next
// dev` and the production server), in the Node runtime — this is the frontend's equivalent of the
// backend's check_fail_closed_config() lifespan check (senior review #44, item J).
import { checkFailClosedConfig } from "@/lib/auth/fail-closed";

export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  checkFailClosedConfig(process.env);
}
