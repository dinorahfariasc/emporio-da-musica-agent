"use client";

import { useMessages } from "@/lib/i18n";

export function TypingIndicator() {
  const messages = useMessages();
  return (
    <div role="status" className="flex justify-start">
      <span className="animate-pulse rounded-2xl bg-muted px-3.5 py-2.5 text-sm text-muted-foreground motion-reduce:animate-none">
        {messages.status.typing}
      </span>
    </div>
  );
}
