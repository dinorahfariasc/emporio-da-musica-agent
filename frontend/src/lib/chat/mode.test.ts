import { describe, expect, it } from "vitest";

import { chatMode } from "@/lib/chat/mode";

describe("chatMode", () => {
  it("fails closed to backend in production when unset", () => {
    expect(chatMode({ NODE_ENV: "production" })).toBe("backend");
  });

  it("defaults to mock outside production", () => {
    expect(chatMode({ NODE_ENV: "development" })).toBe("mock");
  });

  it("treats an empty or unknown value as backend", () => {
    expect(chatMode({ NODE_ENV: "development", CHAT_MODE: "" })).toBe("backend");
    expect(chatMode({ NODE_ENV: "development", CHAT_MODE: "fixtures" })).toBe("backend");
  });

  it("lets an explicit value win", () => {
    expect(chatMode({ NODE_ENV: "production", CHAT_MODE: "mock" })).toBe("mock");
    expect(chatMode({ NODE_ENV: "development", CHAT_MODE: "backend" })).toBe("backend");
  });
});
