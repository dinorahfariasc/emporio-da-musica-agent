"use client";

import { ArrowUp, Square } from "lucide-react";
import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useMessages } from "@/lib/i18n";

export const MAX_MESSAGE_LENGTH = 2000;

type ChatInputProps = {
  disabled: boolean;
  busy: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
};

export function ChatInput({ disabled, busy, onSend, onStop }: ChatInputProps) {
  const messages = useMessages();
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const canSend = !disabled && !busy && text.trim().length > 0;

  function submit() {
    if (!canSend) return;
    onSend(text.trim());
    setText("");
    textareaRef.current?.focus();
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
    <form onSubmit={handleSubmit} className="flex items-end gap-2">
      <Textarea
        ref={textareaRef}
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        maxLength={MAX_MESSAGE_LENGTH}
        rows={1}
        placeholder={messages.input.placeholder}
        aria-label={messages.input.label}
        className="max-h-40 min-h-11 resize-none"
      />
      {busy ? (
        <Button
          type="button"
          variant="outline"
          size="icon-lg"
          className="size-11"
          onClick={onStop}
          disabled={disabled}
          aria-label={messages.input.stop}
        >
          <Square className="fill-current" />
        </Button>
      ) : (
        <Button
          type="submit"
          size="icon-lg"
          className="size-11"
          disabled={!canSend}
          aria-label={messages.input.send}
        >
          <ArrowUp />
        </Button>
      )}
    </form>
  );
}
