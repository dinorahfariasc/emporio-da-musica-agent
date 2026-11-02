"use client";

import type { ChatStatus } from "ai";
import type { ReactNode, RefObject } from "react";

import { ChatHeader } from "@/components/chat/chat-header";
import { ChatInput, type InputLock } from "@/components/chat/chat-input";
import { EmptyState } from "@/components/chat/empty-state";
import { MessageList } from "@/components/chat/message-list";
import { TypingIndicator } from "@/components/chat/typing-indicator";
import type { ChatMessage } from "@/lib/chat/types";
import { cn } from "@/lib/utils";

export type ChatViewProps = {
  messages: ChatMessage[];
  status: ChatStatus;
  typing: boolean;
  /** Banner after the conversation (rate limit, budget, server error). */
  banner?: ReactNode;
  /** Shown inside Melody's column under the last answer (stopped notice, dropped stream). */
  answerFooter?: ReactNode;
  inputRef?: RefObject<HTMLTextAreaElement | null>;
  inputDisabled: boolean;
  inputLock?: InputLock | null;
  busy: boolean;
  onSend: (text: string) => boolean;
  onStop: () => void;
  onNewChat?: () => void;
  /** Replaces the full-page header (the store widget brings its own Melody header); a function
   * receives the "New chat" action. */
  header?: ReactNode | ((onNewChat?: () => void) => ReactNode);
  /** Fills its container (store widget) instead of the viewport. */
  embedded?: boolean;
};

// Presentational chat screen shared by the live chat, the store widget and the dev gallery.
// The body uses container queries (`@3xl:` = 768 px), so a full page gets the desktop layout
// and the narrow widget panel gets the phone layout at any viewport.
export function ChatView({
  messages,
  status,
  typing,
  banner,
  answerFooter,
  inputRef,
  inputDisabled,
  inputLock,
  busy,
  onSend,
  onStop,
  onNewChat,
  header,
  embedded = false,
}: ChatViewProps) {
  // Inside the store widget the page already has its <main>, so the body is a plain <div>.
  const Body = embedded ? "div" : "main";
  return (
    <div className={cn("@container flex flex-col bg-canvas", embedded ? "min-h-0 flex-1" : "h-dvh")}>
      {header === undefined ? (
        <ChatHeader onNewChat={onNewChat} />
      ) : typeof header === "function" ? (
        header(onNewChat)
      ) : (
        header
      )}
      {messages.length === 0 ? (
        <Body className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <EmptyState onPick={onSend} />
        </Body>
      ) : (
        <Body className="flex min-h-0 flex-1 flex-col">
          <MessageList messages={messages} status={status} answerFooter={answerFooter}>
            {typing && <TypingIndicator />}
            {banner}
          </MessageList>
        </Body>
      )}
      <div
        className={cn(
          "shrink-0 bg-linear-to-t from-canvas from-70% to-transparent pt-3 pr-[max(16px,env(safe-area-inset-right))] pl-[max(16px,env(safe-area-inset-left))] @3xl:px-0 @3xl:pt-4 @3xl:pb-6",
          embedded
            ? "pb-[max(16px,calc(12px+env(safe-area-inset-bottom)))]"
            : "pb-[max(34px,calc(12px+env(safe-area-inset-bottom)))]",
        )}
      >
        <div className="mx-auto w-full max-w-(--size-content-max)">
          <ChatInput
            inputRef={inputRef}
            disabled={inputDisabled}
            lock={inputLock}
            busy={busy}
            onSend={onSend}
            onStop={onStop}
          />
        </div>
      </div>
    </div>
  );
}
