"use client";

import { Markdown } from "@/components/chat/markdown";
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
          "flex max-w-[85%] min-w-0 flex-col gap-2 rounded-2xl px-3.5 py-2.5 text-sm sm:max-w-[75%]",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground",
        )}
      >
        {message.parts.map((part, index) => {
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
