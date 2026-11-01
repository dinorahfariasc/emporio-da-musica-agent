import { describe, expect, it } from "vitest";

import { isPublic, isSameSitePath, safeCallbackPath } from "./request-guards";

const ORIGIN = "https://emporio-da-musica-agent.vercel.app";

describe("isPublic", () => {
  it("matches /login and its sub-paths", () => {
    expect(isPublic("/login")).toBe(true);
    expect(isPublic("/login/")).toBe(true);
  });

  it("matches the Auth.js and health routes", () => {
    expect(isPublic("/api/auth/session")).toBe(true);
    expect(isPublic("/api/health")).toBe(true);
  });

  it("does not match the chat page or the chat API", () => {
    expect(isPublic("/")).toBe(false);
    expect(isPublic("/api/chat")).toBe(false);
  });
});

describe("safeCallbackPath", () => {
  it("accepts a relative path and preserves query/hash", () => {
    expect(safeCallbackPath("/some/page?x=1#y", ORIGIN)).toBe("/some/page?x=1#y");
  });

  it("falls back to / for null or empty", () => {
    expect(safeCallbackPath(null, ORIGIN)).toBe("/");
    expect(safeCallbackPath("", ORIGIN)).toBe("/");
  });

  it("falls back to / for an absolute or protocol-relative URL", () => {
    expect(safeCallbackPath("https://evil.example/phish", ORIGIN)).toBe("/");
    expect(safeCallbackPath("//evil.example/phish", ORIGIN)).toBe("/");
  });

  it("falls back to / for a value not starting with a single slash", () => {
    expect(safeCallbackPath("evil.example", ORIGIN)).toBe("/");
  });

  it("rejects a backslash that a browser would normalize into a protocol-relative URL", () => {
    // Browsers treat "/\evil.example" as "//evil.example" (protocol-relative) even though the
    // raw string starts with a single "/" and would pass a naive `startsWith("/")` check.
    expect(safeCallbackPath("/\\evil.example", ORIGIN)).toBe("/");
    expect(safeCallbackPath("/\\/evil.example", ORIGIN)).toBe("/");
  });

  it("rejects control characters", () => {
    expect(safeCallbackPath("/\u0000evil", ORIGIN)).toBe("/");
    expect(safeCallbackPath("/\tevil", ORIGIN)).toBe("/");
  });
});

describe("isSameSitePath", () => {
  it("accepts a relative path", () => {
    expect(isSameSitePath("/some/page?x=1", ORIGIN)).toBe(true);
  });

  it("rejects an absolute, protocol-relative, or backslash-normalized URL", () => {
    expect(isSameSitePath("https://evil.example/phish", ORIGIN)).toBe(false);
    expect(isSameSitePath("//evil.example/phish", ORIGIN)).toBe(false);
    expect(isSameSitePath("/\\evil.example", ORIGIN)).toBe(false);
  });

  it("rejects null or empty", () => {
    expect(isSameSitePath(null, ORIGIN)).toBe(false);
    expect(isSameSitePath("", ORIGIN)).toBe(false);
  });
});
