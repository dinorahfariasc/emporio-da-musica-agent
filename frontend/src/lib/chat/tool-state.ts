import type { ToolUIPart } from "ai";

import type { Messages } from "@/lib/i18n";

export type ToolDisplayState = "running" | "done" | "failed";

export function toToolDisplayState(state: ToolUIPart["state"]): ToolDisplayState {
  switch (state) {
    case "output-available":
      return "done";
    case "output-error":
    case "output-denied":
      return "failed";
    // Approval states are not in the contract (no tool asks for approval); they show as running.
    default:
      return "running";
  }
}

export function toolLabel(toolName: string, messages: Messages): string {
  const labels: Record<string, string> = messages.tools;
  return Object.hasOwn(labels, toolName) ? labels[toolName] : messages.tools.fallback;
}
