import type { ChatMessage } from "@/lib/chat/types";

// The conversation survives a reload in this browser only (nothing server-side). Keeping the
// same id also keeps the backend's per-conversation order verification.
export const HISTORY_KEY = "melody-chat";
export const MAX_STORED_MESSAGES = 40;
// Same rule as the backend's CONVERSATION_ID; anything else would be a 400.
const CONVERSATION_ID = /^[A-Za-z0-9_-]{1,128}$/;

export type StoredChat = { id: string; messages: ChatMessage[] };

export function loadHistory(): StoredChat | null {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return null;
    const data: unknown = JSON.parse(raw);
    if (typeof data !== "object" || data === null) return null;
    const { id, messages } = data as Record<string, unknown>;
    if (typeof id !== "string" || !CONVERSATION_ID.test(id) || !Array.isArray(messages)) {
      return null;
    }
    return { id, messages: messages as ChatMessage[] };
  } catch {
    return null;
  }
}

export function saveHistory(id: string, messages: ChatMessage[]): void {
  try {
    const stored: StoredChat = { id, messages: messages.slice(-MAX_STORED_MESSAGES) };
    localStorage.setItem(HISTORY_KEY, JSON.stringify(stored));
  } catch {
    // Storage disabled or full: the conversation just won't survive a reload.
  }
}

export function clearHistory(): void {
  try {
    localStorage.removeItem(HISTORY_KEY);
  } catch {
    // Nothing to clear.
  }
}
