"use client";

import { getToolName, isToolUIPart } from "ai";

import { Markdown } from "@/components/chat/markdown";
import { ProductCards } from "@/components/chat/product-cards";
import { ToolStatus } from "@/components/chat/tool-status";
import { toToolDisplayState } from "@/lib/chat/tool-state";
import type { ChatMessage } from "@/lib/chat/types";
import { cn } from "@/lib/utils";

type MessageViewProps = { message: ChatMessage; streaming?: boolean };

export function MessageView({ message, streaming = false }: MessageViewProps) {
  const isUser = message.role === "user";

  return (
    <div
      data-testid={`message-${message.role}`}
      className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}
    >
      <div
        className={cn(
          "flex max-w-[85%] min-w-0 flex-col gap-2 px-3.5 py-2.5 text-sm sm:max-w-[75%]",
          isUser
            ? "rounded-2xl rounded-br-md bg-bubble-user text-bubble-user-foreground shadow-sm"
            : "rounded-2xl rounded-bl-md border border-border/70 bg-bubble-assistant text-bubble-assistant-foreground shadow-sm",
        )}
      >
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
          if (part.type !== "text") return null;
          // Customer text is shown verbatim; only Melody's answers are markdown.
          return isUser ? (
            <p key={index} className="break-words whitespace-pre-wrap">
              {part.text}
            </p>
          ) : (
            <Markdown key={index} streaming={streaming && part.state === "streaming"}>
              {part.text}
            </Markdown>
          );
        })}
      </div>
    </div>
  );
}
