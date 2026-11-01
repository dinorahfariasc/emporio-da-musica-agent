import type { ChatMessage } from "@/lib/chat/types";

type Part = ChatMessage["parts"][number];

// What the customer can see: non-empty text, tool status and data cards. `step-start` and
// empty text parts (right after `text-start`) are not content yet.
export function isVisiblePart(part: Part): boolean {
  if (part.type === "text") return part.text.length > 0;
  return part.type.startsWith("tool-") || part.type.startsWith("data-");
}

export function hasVisibleContent(message: ChatMessage | undefined): boolean {
  return !!message && message.parts.some(isVisiblePart);
}
