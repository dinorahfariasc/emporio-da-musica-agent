"use client";

import { Clock } from "lucide-react";
import { useSearchParams } from "next/navigation";

import { Banner } from "@/components/ui/banner";
import { useMessages } from "@/lib/i18n/context";

// Shown when the proxy sent the customer back here because the session expired.
export function LoginNotice() {
  const messages = useMessages();
  const reason = useSearchParams().get("reason");
  if (reason !== "expired") return null;

  return (
    <Banner kind="info" icon={<Clock />} title={messages.login.sessionExpired}>
      {messages.login.sessionExpiredDetail}
    </Banner>
  );
}
