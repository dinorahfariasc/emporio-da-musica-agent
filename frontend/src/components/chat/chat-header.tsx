"use client";

import { useMessages } from "@/lib/i18n/context";

export function ChatHeader() {
  const { app } = useMessages();
  return (
    <header className="flex shrink-0 items-center gap-3 border-b py-3 pl-[max(1rem,env(safe-area-inset-left))] pr-[max(1rem,env(safe-area-inset-right))]">
      <div className="min-w-0">
        <h1 className="truncate text-base font-semibold">{app.assistantName}</h1>
        <p className="truncate text-xs text-muted-foreground">
          {app.tagline} · {app.storeName}
        </p>
      </div>
    </header>
  );
}
