import { APICallError, JSONParseError, TypeValidationError } from "ai";
import { describe, expect, it } from "vitest";

import { toChatError } from "@/lib/chat/errors";
import { getMessages } from "@/lib/i18n";
import { readHttpFixture } from "@/test/fixtures";

const fallback = getMessages().errors.fallback;

function apiError(statusCode: number, responseBody: string): APICallError {
  return new APICallError({
    message: "Request failed",
    url: "/api/chat",
    requestBodyValues: {},
    statusCode,
    responseBody,
  });
}

function fromFixture(name: string): APICallError {
  const spec = readHttpFixture(name);
  return apiError(spec.status, JSON.stringify(spec.body));
}

describe("toChatError", () => {
  it("maps 401 to unauthorized", () => {
    expect(toChatError(fromFixture("http-401"))).toEqual({ kind: "unauthorized" });
  });

  it("maps 429 rate_limited with the body message and retry delay", () => {
    expect(toChatError(fromFixture("http-429-rate-limited"))).toEqual({
      kind: "rate_limited",
      message: readHttpFixture("http-429-rate-limited").body.error.message,
      retryAfterSeconds: 30,
    });
  });

  it("defaults rate_limited to 60 s when retryAfterSeconds is missing", () => {
    const body = { error: { code: "rate_limited", message: "Aguarde." } };
    expect(toChatError(apiError(429, JSON.stringify(body)))).toEqual({
      kind: "rate_limited",
      message: "Aguarde.",
      retryAfterSeconds: 60,
    });
  });

  it("maps 429 budget_exhausted with the body message", () => {
    expect(toChatError(fromFixture("http-429-budget-exhausted"))).toEqual({
      kind: "budget_exhausted",
      message: readHttpFixture("http-429-budget-exhausted").body.error.message,
    });
  });

  it("maps 500 to retryable with the body message", () => {
    expect(toChatError(fromFixture("http-500"))).toEqual({
      kind: "retryable",
      message: readHttpFixture("http-500").body.error.message,
    });
  });

  it("maps 400 invalid_request to retryable", () => {
    const body = { error: { code: "invalid_request", message: "Mensagem inválida." } };
    expect(toChatError(apiError(400, JSON.stringify(body)))).toEqual({
      kind: "retryable",
      message: "Mensagem inválida.",
    });
  });

  it("uses the fallback for a non-JSON body", () => {
    expect(toChatError(apiError(502, "<html>Bad gateway</html>"))).toEqual({
      kind: "retryable",
      message: fallback,
    });
  });

  it("shows the errorText of a mid-stream error chunk (bare Error)", () => {
    expect(toChatError(new Error("Tive um problema para consultar."))).toEqual({
      kind: "retryable",
      message: "Tive um problema para consultar.",
    });
  });

  it.each([
    ["TypeValidationError", new TypeValidationError({ value: {}, cause: "bad" })],
    ["JSONParseError", new JSONParseError({ text: "{", cause: "bad" })],
    ["fetch failure", new TypeError("Failed to fetch")],
    ["AbortError", new DOMException("The operation was aborted.", "AbortError")],
  ])("never shows the text of a %s", (_name, error) => {
    expect(toChatError(error as Error)).toEqual({ kind: "retryable", message: fallback });
  });
});
