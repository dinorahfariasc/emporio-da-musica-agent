"use client";

import { useMessages } from "@/lib/i18n";

export function ChatHeader() {
  const { app } = useMessages();
  return (
    <header className="flex shrink-0 items-center gap-3 border-b px-4 py-3">
      <div className="min-w-0">
        <h1 className="truncate text-base font-semibold">{app.assistantName}</h1>
        <p className="truncate text-xs text-muted-foreground">
          {app.tagline} · {app.storeName}
        </p>
      </div>
    </header>
  );
}
