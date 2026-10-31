"use client";

import { AlertCircle, Check, Loader2 } from "lucide-react";

import { toolLabel, type ToolDisplayState } from "@/lib/chat/tool-state";
import { useMessages } from "@/lib/i18n/context";
import { cn } from "@/lib/utils";

type ToolStatusProps = { toolName: string; state: ToolDisplayState };

// Shows only the catalog label and state: never the tool name, input, output or errorText.
export function ToolStatus({ toolName, state }: ToolStatusProps) {
  const messages = useMessages();
  const label = toolLabel(toolName, messages);
  const suffix = state === "running" ? "" : ` ${messages.toolState[state]}`;

  return (
    <div
      role="status"
      data-state={state}
      className={cn(
        "flex items-center gap-1.5 text-xs",
        state === "failed" ? "text-muted-foreground" : "text-foreground/80",
      )}
    >
      {state === "running" && (
        <Loader2 aria-hidden className="size-3.5 animate-spin motion-reduce:animate-none" />
      )}
      {state === "done" && <Check aria-hidden className="size-3.5" />}
      {state === "failed" && <AlertCircle aria-hidden className="size-3.5" />}
      <span>{label}</span>
      {/* In the content, not aria-label, so the state change is announced. */}
      {suffix && <span className="sr-only">{suffix}</span>}
    </div>
  );
}
