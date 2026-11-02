"use client";

import type { ReactNode } from "react";

import { LanguageSwitch } from "@/components/chat/language-switch";
import { Logo } from "@/components/ui/brand-mark";
import { useMessages } from "@/lib/i18n/context";

// Mobile: language switch top-right, then logo, title and form on the canvas.
// Desktop: subtle background, header (logo + switch) and the form in a 480 px floating card.
export function LoginScreen({ children }: { children: ReactNode }) {
  const { app, login } = useMessages();
  return (
    <div className="flex min-h-dvh flex-1 flex-col bg-canvas md:bg-subtle">
      <header className="flex h-[60px] items-center justify-end px-4 pt-2 pb-2 md:h-20 md:justify-between md:px-10 md:py-0">
        <Logo name={app.storeName} subtitle={app.tagline} className="hidden md:flex" />
        <LanguageSwitch />
      </header>
      <main className="flex flex-1 flex-col gap-7 px-6 pt-6 pb-10 md:items-center md:justify-center md:px-4 md:pt-0 md:pb-20">
        <Logo name={app.storeName} className="md:hidden" />
        <div className="md:hidden">
          <h1 className="t-title-l">{login.title}</h1>
          <p className="t-body-m mt-1.5 text-secondary-text">{login.subtitle}</p>
        </div>
        <div className="w-full md:max-w-[480px] md:overflow-hidden md:rounded-xl md:bg-surface md:shadow-[var(--elevation-floating)]">
          <p
            aria-hidden
            className="t-label-m hidden h-16 items-center justify-center border-b border-border md:flex"
          >
            {login.title}
          </p>
          <div className="flex flex-col gap-6 md:p-8">
            <div className="hidden md:block">
              <h1 className="t-title-m">{login.welcomeTitle}</h1>
              <p className="t-body-m mt-1.5 text-secondary-text">{login.welcomeSubtitle}</p>
            </div>
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
