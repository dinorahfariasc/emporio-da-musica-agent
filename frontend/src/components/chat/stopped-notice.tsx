"use client";

import { Square } from "lucide-react";

import { useMessages } from "@/lib/i18n/context";

// `.stopped`: shown in Melody's column under a partial answer the customer stopped. Not an error.
export function StoppedNotice() {
  const { status } = useMessages();
  return (
    <p role="status" className="flex items-center gap-1.5 text-[13px] leading-[18px] text-secondary-text">
      <Square aria-hidden className="size-3 fill-current" />
      {status.stopped}
    </p>
  );
}
