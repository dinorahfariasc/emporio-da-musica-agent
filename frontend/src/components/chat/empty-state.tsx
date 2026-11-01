"use client";

import { BrandMark } from "@/components/ui/brand-mark";
import { Button } from "@/components/ui/button";
import { useMessages } from "@/lib/i18n/context";

type EmptyStateProps = { onPick: (text: string) => void };

export function EmptyState({ onPick }: EmptyStateProps) {
  const messages = useMessages();
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-7 px-3 py-10 text-center">
      <BrandMark className="size-14 rounded-2xl" size={56} />
      <p className="font-heading max-w-md text-2xl leading-snug font-medium text-balance">
        {messages.emptyState.greeting}
      </p>
      <ul
        aria-label={messages.emptyState.suggestionsLabel}
        className="grid w-full max-w-xl grid-cols-1 gap-2 sm:grid-cols-2"
      >
        {messages.emptyState.suggestions.map((suggestion) => (
          <li key={suggestion}>
            <Button
              variant="outline"
              className="h-auto min-h-11 w-full justify-start rounded-2xl border-border/90 bg-card/80 px-3.5 py-2.5 text-left text-sm whitespace-normal shadow-sm hover:border-primary/30 hover:bg-secondary/60"
              onClick={() => onPick(suggestion)}
            >
              {suggestion}
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
