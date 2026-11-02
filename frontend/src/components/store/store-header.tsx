"use client";

import { LogIn, LogOut, Menu, X } from "lucide-react";
import Link from "next/link";
import { signOut, useSession } from "next-auth/react";
import { useRef, useState, type KeyboardEvent } from "react";

import { LanguageSwitch } from "@/components/chat/language-switch";
import { ThemeToggle } from "@/components/chat/theme-toggle";
import { Logo } from "@/components/ui/brand-mark";
import { Button, buttonVariants } from "@/components/ui/button";
import { clearHistory } from "@/lib/chat/history";
import { useMessages } from "@/lib/i18n/context";
import { cn } from "@/lib/utils";

import { SIGN_IN_HREF } from "./chat-widget";
import { STORE_SECTIONS } from "./sections";

// Store header, built from the approved chat header (`.header` 64 px / `.header.desk` 80 px):
// logo, PT|EN, theme, Sign in/out. Sections: a scrollable anchor row from 768 px, a menu below.
// Below 420 px the store name is visually hidden (the brand tile stays), as in the chat header.
export function StoreHeader() {
  const copy = useMessages();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  function closeMenu(focusButton = false) {
    setMenuOpen(false);
    if (focusButton) menuButtonRef.current?.focus();
  }

  function handleMenuKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape") closeMenu(true);
  }

  return (
    <header
      onKeyDown={handleMenuKeyDown}
      className="sticky top-0 z-30 border-b border-border bg-canvas pt-[env(safe-area-inset-top)]"
    >
      <div className="flex h-16 items-center justify-between gap-1 pr-[max(10px,env(safe-area-inset-right))] pl-[max(16px,env(safe-area-inset-left))] md:h-20 md:gap-3 md:px-10">
        <a href="#inicio" className="min-w-0 rounded-md no-underline">
          <Logo
            name={copy.app.storeName}
            subtitle={copy.store.hero.eyebrow}
            nameClassName="max-[419px]:sr-only"
            subtitleClassName="hidden md:block"
          />
        </a>
        <div className="flex shrink-0 items-center md:gap-2">
          <LanguageSwitch />
          <ThemeToggle />
          <div className="hidden md:block">
            <AuthAction />
          </div>
          <Button
            ref={menuButtonRef}
            variant="ghost"
            size="icon"
            className="text-primary-text no-underline md:hidden"
            aria-label={menuOpen ? copy.store.nav.closeMenu : copy.store.nav.menu}
            aria-expanded={menuOpen}
            aria-controls="store-menu"
            onClick={() => setMenuOpen((value) => !value)}
          >
            {menuOpen ? <X aria-hidden className="size-5" /> : <Menu aria-hidden className="size-5" />}
          </Button>
        </div>
      </div>
      <nav aria-label={copy.store.nav.label} className="hidden md:block">
        {/* Wraps to a second row when the chat panel narrows the page; nothing is cut off. */}
        <ul className="flex flex-wrap gap-x-0.5 px-8 pb-2">
          {STORE_SECTIONS.map((section) => (
            <li key={section.id} className="shrink-0">
              <a
                href={`#${section.id}`}
                className="inline-flex h-11 items-center rounded-full px-3 text-sm leading-5 font-medium text-secondary-text no-underline transition-colors hover:bg-subtle hover:text-primary-text active:bg-muted"
              >
                {copy.store.nav[section.nav]}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      {menuOpen && (
        <nav
          id="store-menu"
          aria-label={copy.store.nav.label}
          className="absolute inset-x-0 top-full max-h-[calc(100dvh-64px)] overflow-y-auto border-b border-border bg-canvas pb-4 shadow-[var(--elevation-card)] md:hidden"
        >
          <ul className="flex flex-col py-2">
            {STORE_SECTIONS.map((section) => (
              <li key={section.id}>
                <a
                  href={`#${section.id}`}
                  onClick={() => closeMenu()}
                  className="flex min-h-11 items-center px-[max(16px,env(safe-area-inset-left))] t-label-m text-primary-text no-underline active:bg-subtle"
                >
                  {copy.store.nav[section.nav]}
                </a>
              </li>
            ))}
          </ul>
          <div className="border-t border-border px-4 pt-4">
            <AuthAction block />
          </div>
        </nav>
      )}
    </header>
  );
}

// Signed in: Sign out (back to the public store). Signed out: Sign in (returns to `/`).
function AuthAction({ block = false }: { block?: boolean }) {
  const { status } = useSession();
  const { login, store } = useMessages();
  if (status === "authenticated") {
    return (
      <Button
        variant={block ? "secondary" : "ghost"}
        size="sm"
        className={cn("no-underline", block && "w-full")}
        onClick={() => {
          // A shared browser must not show the next person this conversation.
          clearHistory();
          void signOut({ callbackUrl: "/" });
        }}
      >
        <LogOut aria-hidden className="size-[18px]" />
        {login.signOut}
      </Button>
    );
  }
  if (status === "unauthenticated") {
    return (
      <Link
        href={SIGN_IN_HREF}
        className={cn(buttonVariants({ variant: "secondary", size: "sm" }), "no-underline", block && "w-full")}
      >
        <LogIn aria-hidden className="size-[18px]" />
        {store.signIn}
      </Link>
    );
  }
  return null;
}
