"use client";

import { SessionProvider } from "next-auth/react";
import type { ReactNode } from "react";

import { useMessages } from "@/lib/i18n/context";

import { ChatWidget } from "./chat-widget";
import { MusicStaffBackground } from "./music-staff-background";
import { StoreFooter } from "./store-footer";
import { StoreHeader } from "./store-header";
import { OpenChatProvider, useChatWidgetController } from "./use-chat-widget";

type StoreShellProps = {
  children: ReactNode;
  /** Dev gallery only: fixed widget content instead of the live, session-driven chat. */
  chat?: ReactNode;
};

// Public store page frame: header, sections, footer and the Melody chat widget. The session is
// read on the client (SessionProvider), so `/` stays a static prerender.
export function StoreShell({ children, chat }: StoreShellProps) {
  return (
    <SessionProvider>
      <StoreFrame chat={chat}>{children}</StoreFrame>
    </SessionProvider>
  );
}

function StoreFrame({ children, chat }: StoreShellProps) {
  const { store } = useMessages();
  const controller = useChatWidgetController();
  // Mobile sheet or maximised overlay: the page behind is inert, which keeps focus in the chat.
  const sheetOpen = controller.open && (!controller.desktop || controller.maximized);
  return (
    <OpenChatProvider value={controller.openChat}>
      {/* >= 1024 px with the panel open, the page reserves the panel's width (+ 16 px gaps). */}
      <div
        inert={sheetOpen}
        className="relative isolate flex min-h-dvh flex-col lg:in-data-[chat=open]:pr-[412px] xl:in-data-[chat=open]:pr-[432px]"
      >
        <MusicStaffBackground />
        <a
          href="#conteudo"
          className="t-label-s sr-only z-40 rounded-md bg-canvas px-4 py-3 focus:not-sr-only focus:fixed focus:top-2 focus:left-2"
        >
          {store.skipToContent}
        </a>
        <StoreHeader />
        <main id="conteudo" tabIndex={-1} className="flex-1 outline-none">
          {children}
        </main>
        <StoreFooter />
      </div>
      <ChatWidget controller={controller} content={chat} />
    </OpenChatProvider>
  );
}
