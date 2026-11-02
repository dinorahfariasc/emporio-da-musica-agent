"use client";

import { useChat } from "@ai-sdk/react";
import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";

import { ChatError } from "@/components/chat/chat-error";
import type { InputLock } from "@/components/chat/chat-input";
import { ChatView } from "@/components/chat/chat-view";
import { StoppedNotice } from "@/components/chat/stopped-notice";
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
  const [rateSecondsLeft, setRateSecondsLeft] = useState(0);
  const [locked, setLocked] = useState(false);
  // Remounts ChatError per error so a repeated rate limit always restarts its countdown.
  const [errorKey, setErrorKey] = useState(0);
  // The customer pressed Stop: the partial answer stays, with a note under it.
  const [stopped, setStopped] = useState(false);

  // A stream closed without its `finish` chunk ends as `ready` with no error (research R2).
  const [droppedStream, setDroppedStream] = useState(false);
  const { messages, sendMessage, regenerate, stop, status, error, clearError } =
    useChat<ChatMessage>({
      transport,
      onError: (error) => {
        const chatError = toChatError(error, copy);
        setErrorKey((key) => key + 1);
        if (chatError.kind === "unauthorized") router.replace("/login?reason=expired&callbackUrl=/");
        if (chatError.kind === "rate_limited") {
          setRateLimited(true);
          setRateSecondsLeft(chatError.retryAfterSeconds);
        }
        if (chatError.kind === "budget_exhausted") setLocked(true);
      },
      onFinish: ({ isAbort, isError }) => {
        if (isAbort) setStopped(true);
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
    setStopped(false);
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

  const errorBanner =
    chatError && !busy ? (
      <ChatError
        key={errorKey}
        error={chatError}
        variant={droppedStream ? "dropped" : "default"}
        onRetry={handleRetry}
        onExpire={() => setRateLimited(false)}
        onTick={setRateSecondsLeft}
      />
    ) : null;

  const inputLock: InputLock | null = locked
    ? { reason: "budget" }
    : rateLimitedUntilExpire
      ? { reason: "rate_limited", seconds: rateSecondsLeft }
      : null;

  return (
    <ChatView
      messages={messages}
      status={status}
      typing={typing}
      banner={droppedStream ? null : errorBanner}
      answerFooter={
        droppedStream ? errorBanner : stopped && !busy ? <StoppedNotice /> : null
      }
      inputRef={inputRef}
      inputDisabled={locked || rateLimitedUntilExpire}
      inputLock={inputLock}
      busy={busy}
      onSend={handleSend}
      onStop={stop}
    />
  );
}
