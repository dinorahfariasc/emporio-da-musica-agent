"use client";

import { LogOut } from "lucide-react";
import { signOut } from "next-auth/react";

import { LanguageSwitch } from "@/components/chat/language-switch";
import { ThemeToggle } from "@/components/chat/theme-toggle";
import { Logo } from "@/components/ui/brand-mark";
import { Button } from "@/components/ui/button";
import { useMessages } from "@/lib/i18n/context";

// `.header` (64 px, mobile) / `.header.desk` (80 px, 40 px gutters). Mobile hides the logo
// subtitle and shows Sign out as a 44 px icon button; desktop shows the label. The theme toggle
// sits between PT|EN and Sign out.
export function ChatHeader() {
  const { app, login } = useMessages();
  // Mobile: 10 px right gutter (the 44 px icon buttons carry their own whitespace). Below 420 px
  // the store name, PT|EN, theme and Sign out do not all fit, so the name is visually hidden
  // (still read by screen readers) and the brand tile stays.
  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-1 border-b border-border bg-canvas pl-[max(16px,env(safe-area-inset-left))] pr-[max(10px,env(safe-area-inset-right))] md:h-20 md:gap-3 md:px-10">
      <Logo
        name={app.storeName}
        subtitle={app.tagline}
        nameClassName="max-[419px]:sr-only"
        subtitleClassName="hidden md:block"
      />
      <div className="flex shrink-0 items-center md:gap-2">
        <LanguageSwitch />
        <ThemeToggle />
        <Button
          variant="ghost"
          size="sm"
          className="size-11 rounded-full px-0 no-underline md:w-auto md:rounded-md md:px-4"
          onClick={() => signOut({ callbackUrl: "/login" })}
        >
          <LogOut aria-hidden className="size-5 md:size-[18px]" />
          <span className="sr-only md:not-sr-only">{login.signOut}</span>
        </Button>
      </div>
    </header>
  );
}
