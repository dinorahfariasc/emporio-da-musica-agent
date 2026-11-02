"use client";

import type { ReactNode } from "react";

import { MelodyAvatar } from "@/components/ui/brand-mark";
import { useMessages } from "@/lib/i18n/context";

// `.melody`: 32 px avatar, then a column with the name and Melody's content (8 px apart).
export function MelodyRow({ children }: { children: ReactNode }) {
  const { app } = useMessages();
  return (
    <div className="flex max-w-full items-start gap-2.5">
      <MelodyAvatar />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <p aria-hidden className="text-[13px] leading-4 font-semibold text-secondary-text">
          {app.assistantName}
        </p>
        {children}
      </div>
    </div>
  );
}

