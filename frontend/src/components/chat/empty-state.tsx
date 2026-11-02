"use client";

import { MelodyAvatar } from "@/components/ui/brand-mark";
import { useMessages } from "@/lib/i18n/context";

type EmptyStateProps = { onPick: (text: string) => void };

// Mobile: left-aligned block sitting just above the composer. Desktop: centred column.
export function EmptyState({ onPick }: EmptyStateProps) {
  const { emptyState } = useMessages();
  return (
    <div className="mx-auto flex w-full max-w-(--size-content-max) flex-1 flex-col justify-end px-4 pt-5 pb-2 md:justify-center md:px-0 md:pt-8">
      <div className="mb-2 flex flex-col gap-6 md:mb-0 md:items-center md:gap-8 md:text-center">
        <div className="flex flex-col gap-3 md:items-center md:gap-8">
          <MelodyAvatar className="size-14 md:size-[72px]" iconClassName="size-7 md:size-9" />
          <div>
            <h1 className="t-title-l md:t-display">{emptyState.greeting}</h1>
            <p className="t-body-l mt-3 text-secondary-text md:mx-auto md:max-w-[560px]">
              {emptyState.intro}
            </p>
          </div>
        </div>
        <div className="md:max-w-[640px]">
          <h2 className="t-label-s mb-2.5 md:sr-only">{emptyState.suggestionsLabel}</h2>
          <ul className="flex flex-wrap gap-2 md:justify-center">
            {emptyState.suggestions.map((suggestion) => (
              <li key={suggestion}>
                <button
                  type="button"
                  onClick={() => onPick(suggestion)}
                  className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-full border border-border bg-canvas px-4 py-2.5 text-left text-sm leading-5 font-medium text-primary-text transition-colors active:border-strong active:bg-subtle"
                >
                  {suggestion}
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
