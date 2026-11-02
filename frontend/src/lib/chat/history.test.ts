// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearHistory, HISTORY_KEY, loadHistory, MAX_STORED_MESSAGES, saveHistory } from "@/lib/chat/history";
import type { ChatMessage } from "@/lib/chat/types";

function message(id: string, role: "user" | "assistant", text: string): ChatMessage {
  return { id, role, parts: [{ type: "text", text }] } as ChatMessage;
}

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe("chat history", () => {
  it("returns null when nothing was saved", () => {
    expect(loadHistory()).toBeNull();
  });

  it("round-trips the conversation id and its messages", () => {
    const messages = [message("u1", "user", "Oi"), message("a1", "assistant", "Olá!")];
    saveHistory("chat-abc", messages);

    expect(loadHistory()).toEqual({ id: "chat-abc", messages });
  });

  it("keeps only the most recent messages", () => {
    const many = Array.from({ length: MAX_STORED_MESSAGES + 5 }, (_, i) =>
      message(`m${i}`, i % 2 ? "assistant" : "user", `t${i}`),
    );
    saveHistory("chat-abc", many);

    const stored = loadHistory();
    expect(stored?.messages).toHaveLength(MAX_STORED_MESSAGES);
    expect(stored?.messages.at(-1)?.id).toBe(`m${MAX_STORED_MESSAGES + 4}`);
  });

  it("ignores corrupt or foreign data instead of crashing", () => {
    localStorage.setItem(HISTORY_KEY, "{not json");
    expect(loadHistory()).toBeNull();

    localStorage.setItem(HISTORY_KEY, JSON.stringify({ id: "bad id!", messages: [] }));
    expect(loadHistory()).toBeNull();

    localStorage.setItem(HISTORY_KEY, JSON.stringify({ id: "chat-abc", messages: "nope" }));
    expect(loadHistory()).toBeNull();
  });

  it("clears the saved conversation", () => {
    saveHistory("chat-abc", [message("u1", "user", "Oi")]);
    clearHistory();

    expect(loadHistory()).toBeNull();
  });

  it("works without storage (private mode) by doing nothing", () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("denied");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("denied");
    });

    expect(() => saveHistory("chat-abc", [])).not.toThrow();
    expect(loadHistory()).toBeNull();
  });
});