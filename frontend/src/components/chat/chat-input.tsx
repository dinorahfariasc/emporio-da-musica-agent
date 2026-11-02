"use client";

import { ArrowUp, Square } from "lucide-react";
import { useState, type FormEvent, type KeyboardEvent, type RefObject } from "react";

import { format } from "@/lib/i18n";
import { useMessages } from "@/lib/i18n/context";
import { cn } from "@/lib/utils";

export const MAX_MESSAGE_LENGTH = 2000;

export type InputLock = { reason: "rate_limited"; seconds: number } | { reason: "budget" };

type ChatInputProps = {
  inputRef?: RefObject<HTMLTextAreaElement | null>;
  disabled: boolean;
  busy: boolean;
  /** Why the input is locked; picks the placeholder. */
  lock?: InputLock | null;
  /** Returns false when the send was not started; the text is then kept. */
  onSend: (text: string) => boolean;
  onStop: () => void;
};

const ICON_BUTTON =
  "grid size-11 shrink-0 cursor-pointer place-items-center rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus";

// Composer (`.composer`): pill textarea + send/stop. States: empty, text, streaming (stop),
// rate limited and budget (locked, with the reason as placeholder).
export function ChatInput({ inputRef, disabled, busy, lock = null, onSend, onStop }: ChatInputProps) {
  const messages = useMessages();
  const [text, setText] = useState("");
  const canSend = !disabled && !busy && text.trim().length > 0;

  const placeholder = disabled && lock
    ? lock.reason === "rate_limited"
      ? format(messages.input.rateLimitedPlaceholder, { seconds: lock.seconds })
      : messages.input.budgetPlaceholder
    : busy
      ? messages.input.streamingPlaceholder
      : messages.input.placeholder;

  function submit() {
    if (!canSend) return;
    if (onSend(text.trim())) setText("");
    inputRef?.current?.focus();
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    submit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <div
        data-disabled={disabled || undefined}
        className={cn(
          "flex min-h-14 items-end gap-2 rounded-2xl border border-border bg-canvas py-[5px] pr-[5px] pl-5 shadow-[var(--elevation-floating)] has-[textarea:focus-visible]:border-2 has-[textarea:focus-visible]:border-focus has-[textarea:focus-visible]:py-1 has-[textarea:focus-visible]:pr-1 has-[textarea:focus-visible]:pl-[19px]",
          disabled && "bg-subtle shadow-none",
        )}
      >
        <textarea
          ref={inputRef}
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          maxLength={MAX_MESSAGE_LENGTH}
          rows={1}
          placeholder={placeholder}
          aria-label={messages.input.label}
          className="field-sizing-content max-h-40 min-h-11 min-w-0 flex-1 resize-none bg-transparent py-2.5 text-base leading-6 text-primary-text outline-none placeholder:text-secondary-text disabled:cursor-not-allowed"
        />
        {busy ? (
          <button
            type="button"
            className={cn(ICON_BUTTON, "bg-inverse text-canvas active:opacity-80")}
            onClick={onStop}
            disabled={disabled}
            aria-label={messages.input.stop}
          >
            <Square aria-hidden className="size-3.5 fill-current" />
          </button>
        ) : (
          <button
            type="submit"
            className={cn(
              ICON_BUTTON,
              "bg-action text-on-accent active:bg-action-pressed disabled:cursor-default disabled:bg-muted disabled:text-disabled",
            )}
            disabled={!canSend}
            aria-label={messages.input.send}
          >
            <ArrowUp aria-hidden className="size-5" strokeWidth={2.4} />
          </button>
        )}
      </div>
      {!disabled && (
        <p className="mt-2 hidden text-center text-xs leading-4 text-secondary-text @3xl:block">
          {messages.input.hint}
        </p>
      )}
    </form>
  );
}
