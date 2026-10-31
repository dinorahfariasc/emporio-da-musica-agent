"use client";

import { AlertCircle } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { ChatErrorState } from "@/lib/chat/errors";
import { useMessages } from "@/lib/i18n/context";

type ChatErrorProps = { error: ChatErrorState; onRetry: () => void };

// Retryable notice. Rate-limit countdown and budget lock arrive with US3.
export function ChatError({ error, onRetry }: ChatErrorProps) {
  const messages = useMessages();
  if (error.kind === "unauthorized") return null;

  return (
    <Alert variant="destructive">
      <AlertCircle />
      <AlertDescription className="flex flex-col items-start gap-2">
        <span>{error.message || messages.errors.fallback}</span>
        {error.kind === "retryable" && (
          <Button variant="outline" className="min-h-11" onClick={onRetry}>
            {messages.errors.retry}
          </Button>
        )}
      </AlertDescription>
    </Alert>
  );
}
