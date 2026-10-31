"use client";

import { AlertCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { ChatErrorState } from "@/lib/chat/errors";
import { format } from "@/lib/i18n";
import { useMessages } from "@/lib/i18n/context";

type ChatErrorProps = {
  error: ChatErrorState;
  onRetry: () => void;
  /** Called once when a rate-limit countdown reaches zero. */
  onExpire: () => void;
};

function useCountdown(seconds: number, onExpire: () => void): number {
  const [remaining, setRemaining] = useState(seconds);
  const onExpireRef = useRef(onExpire);
  useEffect(() => {
    onExpireRef.current = onExpire;
  });

  useEffect(() => {
    if (seconds <= 0) return;
    let left = seconds;
    const id = setInterval(() => {
      left -= 1;
      setRemaining(left);
      if (left <= 0) {
        clearInterval(id);
        onExpireRef.current();
      }
    }, 1000);
    return () => clearInterval(id);
  }, [seconds]);

  return remaining;
}

export function ChatError({ error, onRetry, onExpire }: ChatErrorProps) {
  const messages = useMessages();
  const remaining = useCountdown(
    error.kind === "rate_limited" ? error.retryAfterSeconds : 0,
    onExpire,
  );
  if (error.kind === "unauthorized") return null;

  const waiting = error.kind === "rate_limited" && remaining > 0;
  const canRetry = error.kind === "retryable" || (error.kind === "rate_limited" && !waiting);

  return (
    <Alert variant="destructive">
      <AlertCircle />
      <AlertDescription className="flex flex-col items-start gap-2">
        <span>{error.message || messages.errors.fallback}</span>
        {waiting && (
          <span aria-live="off">{format(messages.errors.countdown, { seconds: remaining })}</span>
        )}
        {canRetry && (
          <Button variant="outline" className="min-h-11" onClick={onRetry}>
            {messages.errors.retry}
          </Button>
        )}
      </AlertDescription>
    </Alert>
  );
}
