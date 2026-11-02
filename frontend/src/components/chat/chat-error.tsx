"use client";

import { CircleAlert, Clock, Moon, RefreshCw, WifiOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Banner } from "@/components/ui/banner";
import { Button } from "@/components/ui/button";
import { RichText } from "@/components/ui/rich-text";
import type { ChatErrorState } from "@/lib/chat/errors";
import { format } from "@/lib/i18n";
import { useMessages } from "@/lib/i18n/context";

type ChatErrorProps = {
  error: ChatErrorState;
  onRetry: () => void;
  /** Called once when a rate-limit countdown reaches zero. */
  onExpire: () => void;
  /** Called every second of a rate-limit countdown (the composer mirrors it). */
  onTick?: (remaining: number) => void;
  /** "dropped": the stream closed before Melody finished (shown in Melody's column). */
  variant?: "default" | "dropped";
};

function useCountdown(seconds: number, onExpire: () => void, onTick?: (left: number) => void): number {
  const [remaining, setRemaining] = useState(seconds);
  const callbacks = useRef({ onExpire, onTick });
  useEffect(() => {
    callbacks.current = { onExpire, onTick };
  });

  useEffect(() => {
    if (seconds <= 0) return;
    let left = seconds;
    const id = setInterval(() => {
      left -= 1;
      setRemaining(left);
      callbacks.current.onTick?.(left);
      if (left <= 0) {
        clearInterval(id);
        callbacks.current.onExpire();
      }
    }, 1000);
    return () => clearInterval(id);
  }, [seconds]);

  return remaining;
}

/** "0:42" — formats the countdown the backend asked for; never computes a wait of its own. */
function clock(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function RetryButton({ label, disabled, onClick }: { label: string; disabled?: boolean; onClick?: () => void }) {
  return (
    <Button variant="secondary" size="sm" disabled={disabled} onClick={onClick}>
      <RefreshCw aria-hidden />
      {label}
    </Button>
  );
}

// Error and limit banners (`.banner`), announced with role="status". Copy is the catalog's;
// only a retryable error shows the backend's customer-facing message (or the fallback).
export function ChatError({ error, onRetry, onExpire, onTick, variant = "default" }: ChatErrorProps) {
  const messages = useMessages();
  const { errors } = messages;
  const remaining = useCountdown(
    error.kind === "rate_limited" ? error.retryAfterSeconds : 0,
    onExpire,
    onTick,
  );
  if (error.kind === "unauthorized") return null;

  if (variant === "dropped") {
    return (
      <Banner
        kind="error"
        icon={<WifiOff />}
        title={errors.droppedTitle}
        data-testid="chat-error"
        actions={<RetryButton label={errors.retry} onClick={onRetry} />}
      >
        {errors.droppedDetail}
      </Banner>
    );
  }

  if (error.kind === "rate_limited") {
    const waiting = remaining > 0;
    return (
      <Banner
        kind="warning"
        icon={<Clock />}
        title={errors.rateLimitedTitle}
        data-testid="chat-error"
        actions={
          waiting ? (
            <RetryButton disabled label={format(errors.retryIn, { seconds: remaining })} />
          ) : (
            <RetryButton label={errors.retry} onClick={onRetry} />
          )
        }
      >
        {waiting ? (
          // The ticking number is not re-announced every second.
          <span aria-live="off">
            <RichText
              template={errors.rateLimitedDetail}
              values={{ time: <span className="font-bold tabular-nums">{clock(remaining)}</span> }}
            />
          </span>
        ) : (
          errors.rateLimitedReady
        )}
      </Banner>
    );
  }

  if (error.kind === "budget_exhausted") {
    return (
      <Banner kind="info" icon={<Moon />} title={errors.budgetTitle} data-testid="chat-error">
        <RichText
          template={errors.budgetDetail}
          values={{ time: <b className="font-semibold">{errors.budgetResetTime}</b> }}
        />
      </Banner>
    );
  }

  return (
    <Banner
      kind="error"
      icon={<CircleAlert />}
      title={errors.serverTitle}
      data-testid="chat-error"
      actions={<RetryButton label={errors.retry} onClick={onRetry} />}
    >
      {error.message || errors.fallback}
    </Banner>
  );
}
