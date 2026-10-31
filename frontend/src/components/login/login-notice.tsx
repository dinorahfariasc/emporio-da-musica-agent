"use client";

import { useSearchParams } from "next/navigation";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { useMessages } from "@/lib/i18n/context";

export function LoginNotice() {
  const messages = useMessages();
  const reason = useSearchParams().get("reason");
  if (reason !== "expired") return null;

  return (
    <Alert>
      <AlertDescription>{messages.login.sessionExpired}</AlertDescription>
    </Alert>
  );
}
