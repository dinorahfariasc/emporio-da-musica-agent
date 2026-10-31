"use client";

import { useChat } from "@ai-sdk/react";
import { useMemo, useRef, useState } from "react";

import { ChatError } from "@/components/chat/chat-error";
import { ChatHeader } from "@/components/chat/chat-header";
import { ChatInput } from "@/components/chat/chat-input";
import { EmptyState } from "@/components/chat/empty-state";
import { MessageList } from "@/components/chat/message-list";
import { TypingIndicator } from "@/components/chat/typing-indicator";
import { toChatError, type ChatErrorState } from "@/lib/chat/errors";
import { hasVisibleContent } from "@/lib/chat/parts";
import { ChatTransport } from "@/lib/chat/transport";
import type { ChatMessage } from "@/lib/chat/types";
import { useMessages } from "@/lib/i18n/context";

type ChatProps = { fetch?: typeof globalThis.fetch };

export function Chat({ fetch }: ChatProps) {
  const copy = useMessages();
  const transport = useMemo(
    () => new ChatTransport({ api: "/api/chat", fetch }),
    [fetch],
  );
  // A stream closed without its `finish` chunk ends as `ready` with no error (research R2).
  const [droppedStream, setDroppedStream] = useState(false);
  const { messages, sendMessage, regenerate, stop, status, error, clearError } =
    useChat<ChatMessage>({
      transport,
      onFinish: ({ isAbort, isError }) => {
        if (!isAbort && !isError && !transport.sawFinish) setDroppedStream(true);
      },
    });

  // `status` updates asynchronously, so a ref blocks a second send in the same tick (R12).
  const sendingRef = useRef(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const busy = status === "submitted" || status === "streaming";

  function run(request: () => Promise<void>): boolean {
    if (sendingRef.current) return false;
    sendingRef.current = true;
    setDroppedStream(false);
    if (error) clearError();
    void request().finally(() => {
      sendingRef.current = false;
    });
    inputRef.current?.focus();
    return true;
  }

  function handleSend(text: string): boolean {
    return run(() => sendMessage({ text }));
  }

  function handleRetry() {
    run(() => regenerate());
  }

  const chatError: ChatErrorState | null = droppedStream
    ? { kind: "retryable", message: copy.errors.fallback }
    : error
      ? toChatError(error, copy)
      : null;

  const last = messages.at(-1);
  const typing =
    status === "submitted" ||
    (status === "streaming" && !(last?.role === "assistant" && hasVisibleContent(last)));

  return (
    <div className="flex h-dvh flex-col bg-background">
      <ChatHeader />
      {messages.length === 0 ? (
        <main className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <EmptyState onPick={handleSend} />
        </main>
      ) : (
        <main className="flex min-h-0 flex-1 flex-col">
          <MessageList messages={messages} status={status}>
            {typing && <TypingIndicator />}
            {chatError && !busy && <ChatError error={chatError} onRetry={handleRetry} />}
          </MessageList>
        </main>
      )}
      <div className="shrink-0 border-t bg-background px-4 py-3">
        <div className="mx-auto w-full max-w-3xl">
          {/* `disabled` is driven by rate limits and the budget lock in US3. */}
          <ChatInput inputRef={inputRef} disabled={false} busy={busy} onSend={handleSend} onStop={stop} />
        </div>
      </div>
    </div>
  );
}
