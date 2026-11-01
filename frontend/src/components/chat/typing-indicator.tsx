"use client";

import { useMessages } from "@/lib/i18n/context";

export function TypingIndicator() {
  const messages = useMessages();
  return (
    <div role="status" className="flex justify-start">
      <span className="animate-pulse rounded-2xl rounded-bl-md border border-border/70 bg-bubble-assistant px-3.5 py-2.5 text-sm text-muted-foreground shadow-sm motion-reduce:animate-none">
        {messages.status.typing}
      </span>
    </div>
  );
}
