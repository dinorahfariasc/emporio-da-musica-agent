import { describe, expect, it } from "vitest";

import { checkFailClosedConfig } from "./fail-closed";

const VALID = {
  NODE_ENV: "production",
  DATABASE_URL: "postgresql://x",
  BACKEND_URL: "https://backend.example",
  AUTH_SECRET: "a".repeat(32),
  SERVICE_JWT_SECRET: "b".repeat(32),
};

describe("checkFailClosedConfig", () => {
  it("never throws outside production", () => {
    expect(() => checkFailClosedConfig({ NODE_ENV: "development" })).not.toThrow();
  });

  it("does not throw when everything required is configured", () => {
    expect(() => checkFailClosedConfig(VALID)).not.toThrow();
  });

  it("throws when AUTH_SECRET is missing", () => {
    expect(() => checkFailClosedConfig({ ...VALID, AUTH_SECRET: undefined })).toThrow(
      /AUTH_SECRET/,
    );
  });

  it("throws when SERVICE_JWT_SECRET is missing", () => {
    expect(() => checkFailClosedConfig({ ...VALID, SERVICE_JWT_SECRET: undefined })).toThrow(
      /SERVICE_JWT_SECRET/,
    );
  });

  it("throws when a secret is shorter than 32 characters", () => {
    expect(() => checkFailClosedConfig({ ...VALID, AUTH_SECRET: "short" })).toThrow(
      /at least 32 characters/,
    );
  });

  it("throws when DATABASE_URL or BACKEND_URL is missing", () => {
    expect(() => checkFailClosedConfig({ ...VALID, DATABASE_URL: undefined })).toThrow(
      /DATABASE_URL/,
    );
    expect(() => checkFailClosedConfig({ ...VALID, BACKEND_URL: undefined })).toThrow(
      /BACKEND_URL/,
    );
  });

  it("treats VERCEL_ENV=production as production even if NODE_ENV is not set", () => {
    expect(() =>
      checkFailClosedConfig({ VERCEL_ENV: "production", AUTH_SECRET: undefined }),
    ).toThrow();
  });
});
