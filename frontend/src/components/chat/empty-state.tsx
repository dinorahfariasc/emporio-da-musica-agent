"use client";

import { MelodyAvatar } from "@/components/ui/brand-mark";
import { useMessages } from "@/lib/i18n/context";

type EmptyStateProps = { onPick: (text: string) => void };

// Narrow (phone, side panel): left-aligned block just above the composer. Wide container
// (>= 768 px): centred column. Container queries, so the chat adapts to the widget width.
export function EmptyState({ onPick }: EmptyStateProps) {
  const { emptyState } = useMessages();
  return (
    <div className="mx-auto flex w-full max-w-(--size-content-max) flex-1 flex-col justify-end px-4 pt-5 pb-2 @3xl:justify-center @3xl:px-0 @3xl:pt-8">
      <div className="mb-2 flex flex-col gap-6 @3xl:mb-0 @3xl:items-center @3xl:gap-8 @3xl:text-center">
        <div className="flex flex-col gap-3 @3xl:items-center @3xl:gap-8">
          <MelodyAvatar className="size-14 @3xl:size-[72px]" iconClassName="size-7 @3xl:size-9" />
          <div>
            <h2 className="t-title-l @3xl:t-display">{emptyState.greeting}</h2>
            <p className="t-body-l mt-3 text-secondary-text @3xl:mx-auto @3xl:max-w-[560px]">
              {emptyState.intro}
            </p>
          </div>
        </div>
        <div className="@3xl:max-w-[640px]">
          <h3 className="t-label-s mb-2.5 @3xl:sr-only">{emptyState.suggestionsLabel}</h3>
          <ul className="flex flex-wrap gap-2 @3xl:justify-center">
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
