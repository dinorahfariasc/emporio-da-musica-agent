import { describe, expect, it } from "vitest";

import { mockChatResponse } from "@/lib/chat/mock";

async function messageId(): Promise<string> {
  const response = await mockChatResponse({
    messages: [{ role: "user", parts: [{ type: "text", text: "Oi" }] }],
  });
  const text = await response.text();
  return text.match(/"messageId":"([^"]+)"/)![1];
}

describe("mockChatResponse", () => {
  it("sends a new message id per answer, like the backend", async () => {
    const [first, second] = [await messageId(), await messageId()];
    expect(first).not.toBe(second);
  });
});
