import { describe, expect, it } from "vitest";

import { hasVisibleContent, isVisiblePart } from "@/lib/chat/parts";
import type { ChatMessage } from "@/lib/chat/types";

function message(parts: ChatMessage["parts"]): ChatMessage {
  return { id: "m", role: "assistant", parts };
}

describe("visible parts", () => {
  it("ignores step-start and empty text", () => {
    expect(hasVisibleContent(message([{ type: "step-start" }]))).toBe(false);
    expect(hasVisibleContent(message([{ type: "text", text: "", state: "streaming" }]))).toBe(false);
    expect(hasVisibleContent(undefined)).toBe(false);
  });

  it("counts text, tool and data parts", () => {
    expect(isVisiblePart({ type: "text", text: "Oi", state: "streaming" })).toBe(true);
    expect(
      isVisiblePart({ type: "data-products", data: { products: [] } } as ChatMessage["parts"][number]),
    ).toBe(true);
    expect(
      isVisiblePart({
        type: "tool-search_products",
        toolCallId: "t1",
        state: "input-available",
        input: {},
      } as ChatMessage["parts"][number]),
    ).toBe(true);
  });
});
