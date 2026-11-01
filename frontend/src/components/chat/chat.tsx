"use client";

import { useChat } from "@ai-sdk/react";
import { useRouter } from "next/navigation";
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
  const router = useRouter();
  // Rate limit: input locked until the countdown ends. Budget: locked for the page session.
  const [rateLimitedUntilExpire, setRateLimited] = useState(false);
  const [locked, setLocked] = useState(false);
  // Remounts ChatError per error so a repeated rate limit always restarts its countdown.
  const [errorKey, setErrorKey] = useState(0);

  // A stream closed without its `finish` chunk ends as `ready` with no error (research R2).
  const [droppedStream, setDroppedStream] = useState(false);
  const { messages, sendMessage, regenerate, stop, status, error, clearError } =
    useChat<ChatMessage>({
      transport,
      onError: (error) => {
        const kind = toChatError(error, copy).kind;
        setErrorKey((key) => key + 1);
        if (kind === "unauthorized") router.replace("/login?reason=expired&callbackUrl=/");
        if (kind === "rate_limited") setRateLimited(true);
        if (kind === "budget_exhausted") setLocked(true);
      },
      onFinish: ({ isAbort, isError }) => {
        if (!isAbort && !isError && !transport.sawFinish) setDroppedStream(true);
      },
    });

  // `status` updates asynchronously, so a ref blocks a second send in the same tick (R12).
  const sendingRef = useRef(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const busy = status === "submitted" || status === "streaming";

  function run(request: () => Promise<void>): boolean {
    if (sendingRef.current || locked) return false;
    sendingRef.current = true;
    setDroppedStream(false);
    setRateLimited(false);
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
    <div className="flex h-dvh flex-col bg-transparent">
      <ChatHeader />
      {messages.length === 0 ? (
        <main className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <EmptyState onPick={handleSend} />
        </main>
      ) : (
        <main className="flex min-h-0 flex-1 flex-col">
          <MessageList messages={messages} status={status}>
            {typing && <TypingIndicator />}
            {chatError && !busy && (
              <ChatError
                key={errorKey}
                error={chatError}
                onRetry={handleRetry}
                onExpire={() => setRateLimited(false)}
              />
            )}
          </MessageList>
        </main>
      )}
      <div className="shrink-0 border-t border-border/80 bg-card/80 pt-3 pl-[max(1rem,env(safe-area-inset-left))] pr-[max(1rem,env(safe-area-inset-right))] pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur-sm">
        <div className="mx-auto w-full max-w-3xl">
          <ChatInput
            inputRef={inputRef}
            disabled={locked || rateLimitedUntilExpire}
            busy={busy}
            onSend={handleSend}
            onStop={stop}
          />
        </div>
      </div>
    </div>
  );
}
