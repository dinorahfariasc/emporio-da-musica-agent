import { describe, expect, it } from "vitest";

import { isPublic, isSameSitePath } from "./request-guards";

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

describe("isSameSitePath", () => {
  it("accepts a relative path", () => {
    expect(isSameSitePath("/some/page?x=1")).toBe(true);
  });

  it("rejects an absolute or protocol-relative URL (open-redirect guard)", () => {
    expect(isSameSitePath("https://evil.example/phish")).toBe(false);
    expect(isSameSitePath("//evil.example/phish")).toBe(false);
  });

  it("rejects null or empty", () => {
    expect(isSameSitePath(null)).toBe(false);
    expect(isSameSitePath("")).toBe(false);
  });
});
