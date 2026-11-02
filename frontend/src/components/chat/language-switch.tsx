"use client";

import { useLocale, useMessages } from "@/lib/i18n/context";
import type { LocaleCode } from "@/lib/i18n";
import { cn } from "@/lib/utils";

// `.lang` (components.css): pill group, 44 px tall; the active option is bg/inverse.
export function LanguageSwitch({ className }: { className?: string }) {
  const { locale, setLocale } = useLocale();
  const { language } = useMessages();
  const options: { code: LocaleCode; label: string; lang: string }[] = [
    { code: "pt-BR", label: language.pt, lang: "pt-BR" },
    { code: "en", label: language.en, lang: "en" },
  ];

  return (
    <div
      role="group"
      aria-label={language.label}
      className={cn(
        "flex h-11 items-center rounded-full border border-border bg-canvas p-[3px]",
        className,
      )}
    >
      {options.map((option) => {
        const active = option.code === locale;
        return (
          <button
            key={option.code}
            type="button"
            lang={option.lang}
            aria-pressed={active}
            onClick={() => setLocale(option.code)}
            className={cn(
              // 36 px tall inside the 44 px pill; the ::after extends the hit area to 44 px.
              "relative grid h-9 min-w-11 cursor-pointer place-items-center rounded-full px-2 text-[13px] leading-4 font-semibold transition-colors after:absolute after:inset-x-0 after:-inset-y-1",
              active ? "bg-inverse text-on-inverse" : "text-secondary-text active:bg-subtle",
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
