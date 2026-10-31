import { AISDKError, APICallError } from "ai";

import { getMessages, type Messages } from "@/lib/i18n";

export type ChatErrorState =
  | { kind: "unauthorized" }
  | { kind: "rate_limited"; message: string; retryAfterSeconds: number }
  | { kind: "budget_exhausted"; message: string }
  | { kind: "retryable"; message: string };

const DEFAULT_RETRY_AFTER_SECONDS = 60;

type ErrorBody = { code?: unknown; message?: unknown; retryAfterSeconds?: unknown };

function parseBody(responseBody: string | undefined): ErrorBody | null {
  try {
    const parsed: unknown = JSON.parse(responseBody ?? "");
    const error = (parsed as { error?: unknown } | null)?.error;
    return error && typeof error === "object" ? (error as ErrorBody) : null;
  } catch {
    return null;
  }
}

// Only a bare Error carries the contract's user-facing `errorText` (mid-stream `error` chunk).
// SDK, fetch and abort errors carry technical text that must never reach the customer.
function isBareError(error: Error): boolean {
  return error.constructor === Error && !AISDKError.isInstance(error);
}

export function toChatError(error: Error, messages: Messages = getMessages()): ChatErrorState {
  const fallback = messages.errors.fallback;

  if (!APICallError.isInstance(error)) {
    return { kind: "retryable", message: isBareError(error) && error.message ? error.message : fallback };
  }

  if (error.statusCode === 401) return { kind: "unauthorized" };

  const body = parseBody(error.responseBody);
  const message = typeof body?.message === "string" && body.message ? body.message : fallback;

  if (body?.code === "rate_limited") {
    const retryAfter = body.retryAfterSeconds;
    return {
      kind: "rate_limited",
      message,
      retryAfterSeconds:
        typeof retryAfter === "number" && retryAfter > 0 ? retryAfter : DEFAULT_RETRY_AFTER_SECONDS,
    };
  }
  if (body?.code === "budget_exhausted") return { kind: "budget_exhausted", message };

  return { kind: "retryable", message };
}
