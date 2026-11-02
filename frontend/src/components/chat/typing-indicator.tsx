"use client";

import { MelodyRow } from "@/components/chat/melody-row";
import { useMessages } from "@/lib/i18n/context";

// `.typing`: three dots + "Melody está digitando…" in a Melody-shaped bubble.
export function TypingIndicator() {
  const messages = useMessages();
  return (
    <MelodyRow>
      <div
        role="status"
        className="flex items-center gap-2.5 rounded-[6px_20px_20px_20px] bg-bubble-melody px-4 py-3 text-sm leading-5 text-secondary-text"
      >
        <span aria-hidden className="flex gap-1">
          {[0, 1, 2].map((dot) => (
            <i
              key={dot}
              className="block size-1.5 rounded-full bg-secondary-text motion-safe:animate-[melody-dot_1.2s_ease-in-out_infinite]"
              style={{ animationDelay: `${dot * 0.15}s`, opacity: 1 - dot * 0.35 }}
            />
          ))}
        </span>
        {messages.status.typing}
      </div>
    </MelodyRow>
  );
}
