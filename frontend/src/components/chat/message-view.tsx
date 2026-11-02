"use client";

import { getToolName, isToolUIPart } from "ai";
import type { ReactNode } from "react";

import { Markdown } from "@/components/chat/markdown";
import { MelodyRow } from "@/components/chat/melody-row";
import { ProductCards } from "@/components/chat/product-cards";
import { ToolStatus } from "@/components/chat/tool-status";
import { toToolDisplayState } from "@/lib/chat/tool-state";
import type { ChatMessage } from "@/lib/chat/types";

type MessageViewProps = { message: ChatMessage; streaming?: boolean; footer?: ReactNode };

const MELODY_BUBBLE =
  "max-w-full min-w-0 rounded-[6px_20px_20px_20px] bg-bubble-melody px-4 py-3 text-base leading-6 text-primary-text";

// User: dark bubble on the right. Melody: avatar + name, then the parts in stream order —
// tool status lines and product cards sit in the column, answer text inside the bubble.
export function MessageView({ message, streaming = false, footer }: MessageViewProps) {
  if (message.role === "user") {
    return (
      <div data-testid="message-user" className="flex w-full justify-end">
        <div className="max-w-[82%] min-w-0 rounded-[20px_20px_6px_20px] bg-bubble-user px-4 py-3 text-base leading-6 text-bubble-user-foreground">
          {message.parts.map((part, index) =>
            part.type === "text" ? (
              // Customer text is shown verbatim, never as markdown.
              <p key={index} className="break-words whitespace-pre-wrap">
                {part.text}
              </p>
            ) : null,
          )}
        </div>
      </div>
    );
  }

  return (
    <div data-testid={`message-${message.role}`} className="w-full">
      <MelodyRow>
        {message.parts.map((part, index) => {
          if (isToolUIPart(part)) {
            return (
              <ToolStatus
                key={part.toolCallId}
                toolName={getToolName(part)}
                state={toToolDisplayState(part.state)}
              />
            );
          }
          if (part.type === "data-products") {
            return <ProductCards key={part.id ?? index} products={part.data.products} />;
          }
          if (part.type !== "text" || part.text.length === 0) return null;
          return (
            <div key={index} data-testid="assistant-text" className={MELODY_BUBBLE}>
              <Markdown streaming={streaming && part.state === "streaming"}>{part.text}</Markdown>
            </div>
          );
        })}
        {footer}
      </MelodyRow>
    </div>
  );
}
