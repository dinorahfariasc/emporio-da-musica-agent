"use client";

import { Check, X } from "lucide-react";

import { toolLabel, type ToolDisplayState } from "@/lib/chat/tool-state";
import { useMessages } from "@/lib/i18n/context";
import type { Messages } from "@/lib/i18n";
import { cn } from "@/lib/utils";

type ToolStatusProps = { toolName: string; state: ToolDisplayState };

function doneLabel(toolName: string, messages: Messages): string {
  const done: Record<string, string> = messages.toolsDone;
  return Object.hasOwn(done, toolName) ? done[toolName] : done.fallback;
}

// `.status` line: running (spinner + present tense), done (past tense), failed (generic copy).
// Shows only catalog copy: never the tool name, input, output or errorText.
export function ToolStatus({ toolName, state }: ToolStatusProps) {
  const messages = useMessages();
  const label =
    state === "running"
      ? toolLabel(toolName, messages)
      : state === "done"
        ? doneLabel(toolName, messages)
        : messages.toolState.failed;

  return (
    <div
      role="status"
      data-state={state}
      className={cn(
        "flex min-h-6 items-center gap-2 text-sm leading-5 font-medium",
        state === "failed" ? "text-error" : "text-secondary-text",
      )}
    >
      <span
        aria-hidden
        className={cn(
          "grid size-5 shrink-0 place-items-center rounded-full",
          state === "done" && "bg-success-bg text-success",
          state === "failed" && "bg-error-bg text-error",
        )}
      >
        {state === "running" && (
          <span className="block size-3.5 animate-spin rounded-full border-2 border-brand border-r-transparent motion-reduce:animate-none" />
        )}
        {state === "done" && <Check className="size-3" strokeWidth={3} />}
        {state === "failed" && <X className="size-3" strokeWidth={3} />}
      </span>
      <span className="min-w-0">{label}</span>
    </div>
  );
}
