"use client";

import type { ChatStatus } from "ai";
import type { ReactNode, RefObject } from "react";

import { ChatHeader } from "@/components/chat/chat-header";
import { ChatInput, type InputLock } from "@/components/chat/chat-input";
import { EmptyState } from "@/components/chat/empty-state";
import { MessageList } from "@/components/chat/message-list";
import { TypingIndicator } from "@/components/chat/typing-indicator";
import type { ChatMessage } from "@/lib/chat/types";

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
};

// Presentational chat screen shared by the live chat and the dev gallery.
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
}: ChatViewProps) {
  return (
    <div className="flex h-dvh flex-col bg-canvas">
      <ChatHeader />
      {messages.length === 0 ? (
        <main className="flex min-h-0 flex-1 flex-col overflow-y-auto">
          <EmptyState onPick={onSend} />
        </main>
      ) : (
        <main className="flex min-h-0 flex-1 flex-col">
          <MessageList messages={messages} status={status} answerFooter={answerFooter}>
            {typing && <TypingIndicator />}
            {banner}
          </MessageList>
        </main>
      )}
      <div className="shrink-0 bg-linear-to-t from-canvas from-70% to-transparent pt-3 pr-[max(16px,env(safe-area-inset-right))] pb-[max(34px,calc(12px+env(safe-area-inset-bottom)))] pl-[max(16px,env(safe-area-inset-left))] md:px-0 md:pt-4 md:pb-6">
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
