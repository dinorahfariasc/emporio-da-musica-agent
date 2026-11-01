"use client";

import { signOut } from "next-auth/react";

import { Button } from "@/components/ui/button";
import { useMessages } from "@/lib/i18n/context";

export function ChatHeader() {
  const { app, login } = useMessages();
  return (
    <header className="flex shrink-0 items-center gap-3 border-b py-3 pl-[max(1rem,env(safe-area-inset-left))] pr-[max(1rem,env(safe-area-inset-right))]">
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-base font-semibold">{app.assistantName}</h1>
        <p className="truncate text-xs text-muted-foreground">
          {app.tagline} · {app.storeName}
        </p>
      </div>
      <Button variant="ghost" size="sm" onClick={() => signOut({ callbackUrl: "/login" })}>
        {login.signOut}
      </Button>
    </header>
  );
}
