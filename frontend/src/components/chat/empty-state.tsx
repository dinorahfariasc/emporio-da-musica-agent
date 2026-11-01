"use client";

import { Button } from "@/components/ui/button";
import { useMessages } from "@/lib/i18n/context";

type EmptyStateProps = { onPick: (text: string) => void };

export function EmptyState({ onPick }: EmptyStateProps) {
  const messages = useMessages();
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 px-2 py-8 text-center">
      <p className="text-lg font-medium text-balance">{messages.emptyState.greeting}</p>
      <ul
        aria-label={messages.emptyState.suggestionsLabel}
        className="grid w-full max-w-xl grid-cols-1 gap-2 sm:grid-cols-2"
      >
        {messages.emptyState.suggestions.map((suggestion) => (
          <li key={suggestion}>
            <Button
              variant="outline"
              className="h-auto min-h-11 w-full justify-start px-3 py-2 text-left whitespace-normal"
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
