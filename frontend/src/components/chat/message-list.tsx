"use client";

import type { ChatStatus } from "ai";
import { useLayoutEffect, useRef, type ReactNode } from "react";

import { MessageView } from "@/components/chat/message-view";
import { hasVisibleContent } from "@/lib/chat/parts";
import type { ChatMessage } from "@/lib/chat/types";
import { useMessages } from "@/lib/i18n/context";

const STICK_THRESHOLD_PX = 80;

type MessageListProps = {
  messages: ChatMessage[];
  status: ChatStatus;
  children?: ReactNode;
};

function textOf(message: ChatMessage): string {
  return message.parts
    .map((part) => (part.type === "text" ? part.text : ""))
    .join(" ")
    .trim();
}

export function MessageList({ messages, status, children }: MessageListProps) {
  const copy = useMessages();
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickRef = useRef(true);
  const busy = status === "submitted" || status === "streaming";
  const last = messages.at(-1);

  // Announce whole answers once they finish, not every token (the log itself is aria-live off).
  const announcement = !busy && last?.role === "assistant" ? textOf(last) : "";

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (el && stickRef.current) el.scrollTop = el.scrollHeight;
  }, [messages, status, children]);

  function handleScroll() {
    const el = scrollRef.current;
    if (!el) return;
    stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight <= STICK_THRESHOLD_PX;
  }

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      role="log"
      aria-live="off"
      aria-label={copy.messages.logLabel}
      className="flex min-h-0 flex-1 flex-col overflow-x-hidden overflow-y-auto"
    >
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-3.5 py-5 pl-[max(1rem,env(safe-area-inset-left))] pr-[max(1rem,env(safe-area-inset-right))]">
        {messages.map((message, index) =>
          // An assistant message with only `step-start` or empty text is not shown yet; the
          // typing indicator covers it.
          message.role === "assistant" && !hasVisibleContent(message) ? null : (
            <MessageView
              key={message.id}
              message={message}
              streaming={busy && index === messages.length - 1}
            />
          ),
        )}
        {children}
      </div>
      <div aria-live="polite" className="sr-only" data-testid="chat-announcer">
        {announcement}
      </div>
    </div>
  );
}
