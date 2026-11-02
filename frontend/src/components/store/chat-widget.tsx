"use client";

import { ChevronDown, Maximize2, Minimize2, Minus, Music, SquarePen } from "lucide-react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { useId, type KeyboardEvent, type ReactNode } from "react";

import { Chat } from "@/components/chat/chat";
import { MelodyAvatar } from "@/components/ui/brand-mark";
import { Button, Spinner, buttonVariants } from "@/components/ui/button";
import { useMessages } from "@/lib/i18n/context";
import { cn } from "@/lib/utils";

import type { ChatWidgetController } from "./use-chat-widget";

export const CHAT_PANEL_ID = "melody-chat";
export const SIGN_IN_HREF = "/login?callbackUrl=%2F";

type ChatWidgetProps = {
  controller: ChatWidgetController;
  /** Dev gallery only: fixed content instead of the session-driven chat. */
  content?: ReactNode;
};

// Desktop (>= 1024 px): fixed side panel on the right, no focus trap, the page reserves its
// width; it can be maximised to a full-window overlay (modal dialog, page inert, chat in a
// centred reading column). Mobile: full-screen sheet (modal dialog; the page behind is inert).
// Minimised: a floating button (FAB) bottom right, with a dot when Melody answered while it was
// hidden. Visibility comes from <html data-chat>, so the first paint is already right. The same
// panel element is kept in every state, so the conversation is never remounted.
const PANEL_BASE = "fixed inset-0 z-50 hidden flex-col bg-canvas outline-none in-data-[chat=open]:flex";
const PANEL_SIDE =
  "lg:inset-auto lg:top-4 lg:right-4 lg:bottom-4 lg:w-[380px] lg:overflow-hidden lg:rounded-xl lg:border lg:border-border lg:shadow-[var(--elevation-floating)] xl:w-[400px]";
const PANEL_MAX = "motion-safe:animate-in motion-safe:fade-in-0 motion-safe:duration-150";
export function ChatWidget({ controller, content }: ChatWidgetProps) {
  const { widget, app } = useMessages();
  const {
    open,
    desktop,
    maximized,
    unread,
    openChat,
    minimize,
    toggleMaximized,
    restore,
    markActivity,
    fabRef,
    panelRef,
  } = controller;
  const modal = !desktop || maximized;
  const titleId = useId();

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape" && !event.defaultPrevented) {
      event.preventDefault();
      // Esc steps back: maximised -> side panel -> minimised.
      if (maximized) restore();
      else minimize();
    }
  }

  // Melody's header; signed in, the chat passes its "New chat" action.
  function renderHeader(onNewChat?: () => void) {
    return (
      <header className="flex h-16 shrink-0 items-center gap-3 border-b border-border pr-[max(10px,env(safe-area-inset-right))] pl-[max(16px,env(safe-area-inset-left))] max-lg:mt-[env(safe-area-inset-top)] lg:pr-2.5 lg:pl-4">
        <MelodyAvatar className="size-9" iconClassName="size-[18px]" />
        <div className="min-w-0 flex-1">
          <h2 id={titleId} className="t-label-m truncate">
            {widget.title}
          </h2>
          <p className="t-caption truncate text-secondary-text">{widget.subtitle}</p>
        </div>
        {onNewChat ? (
          <Button
            variant="ghost"
            size="icon"
            className="text-primary-text no-underline"
            aria-label={app.newChat}
            title={app.newChat}
            onClick={onNewChat}
          >
            <SquarePen aria-hidden className="size-5" />
          </Button>
        ) : null}
        <Button
          variant="ghost"
          size="icon"
          className="text-primary-text no-underline max-lg:hidden"
          aria-label={maximized ? widget.restore : widget.maximize}
          onClick={toggleMaximized}
        >
          {maximized ? <Minimize2 aria-hidden className="size-5" /> : <Maximize2 aria-hidden className="size-5" />}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="text-primary-text no-underline"
          aria-label={widget.minimize}
          onClick={minimize}
        >
          <ChevronDown aria-hidden className="size-5 lg:hidden" />
          <Minus aria-hidden className="hidden size-5 lg:block" />
        </Button>
      </header>
    );
  }

  return (
    <div data-chat-widget>
      <div
        ref={panelRef}
        id={CHAT_PANEL_ID}
        role={modal ? "dialog" : "complementary"}
        aria-modal={modal ? true : undefined}
        data-maximized={maximized || undefined}
        aria-labelledby={titleId}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className={cn(PANEL_BASE, maximized ? PANEL_MAX : PANEL_SIDE)}
      >
        {content ? (
          <>
            {renderHeader()}
            {content}
          </>
        ) : (
          <SessionChat header={renderHeader} onActivity={markActivity} />
        )}
      </div>
      <button
        ref={fabRef}
        type="button"
        aria-label={unread ? widget.openUnread : widget.open}
        aria-controls={CHAT_PANEL_ID}
        aria-expanded={open}
        onClick={openChat}
        className="fixed right-[max(20px,env(safe-area-inset-right))] bottom-[max(20px,env(safe-area-inset-bottom))] z-40 grid size-14 cursor-pointer place-items-center rounded-full bg-action text-on-accent shadow-[var(--elevation-floating)] transition-colors active:bg-action-pressed in-data-[chat=open]:hidden"
      >
        <Music aria-hidden className="size-6" strokeWidth={2.2} />
        {unread && (
          <span
            data-testid="chat-fab-unread"
            aria-hidden
            className="absolute top-0.5 right-0.5 size-3.5 rounded-full bg-inverse ring-2 ring-canvas"
          />
        )}
      </button>
    </div>
  );
}

// Signed in: the live chat. Signed out: Melody's intro and a way to sign in (back to `/`).
function SessionChat({
  header,
  onActivity,
}: {
  header: (onNewChat?: () => void) => ReactNode;
  onActivity: () => void;
}) {
  const { status } = useSession();
  if (status === "authenticated") return <Chat embedded header={header} onActivity={onActivity} />;
  return (
    <>
      {header()}
      {status === "unauthenticated" ? <SignInPrompt /> : <ChatLoading />}
    </>
  );
}

export function SignInPrompt() {
  const { emptyState, widget, login } = useMessages();
  return (
    <div className="flex min-h-0 flex-1 flex-col justify-end gap-6 overflow-y-auto pt-5 pr-[max(16px,env(safe-area-inset-right))] pb-[max(24px,calc(16px+env(safe-area-inset-bottom)))] pl-[max(16px,env(safe-area-inset-left))]">
      <div className="flex flex-col gap-3">
        <MelodyAvatar className="size-14" iconClassName="size-7" />
        <div>
          <p className="t-title-l">{emptyState.greeting}</p>
          <p className="t-body-l mt-3 text-secondary-text">{emptyState.intro}</p>
        </div>
      </div>
      <div className="flex flex-col gap-3">
        <Link href={SIGN_IN_HREF} className={cn(buttonVariants(), "w-full no-underline")}>
          {widget.signInCta}
        </Link>
        <p className="t-caption text-secondary-text">{login.noAccount}</p>
      </div>
    </div>
  );
}

function ChatLoading() {
  const { widget } = useMessages();
  return (
    <div role="status" className="flex flex-1 items-center justify-center text-secondary-text">
      <Spinner />
      <span className="sr-only">{widget.loading}</span>
    </div>
  );
}
