import { describe, expect, it } from "vitest";

import { toolLabel, toToolDisplayState } from "@/lib/chat/tool-state";
import { getMessages } from "@/lib/i18n";

describe("toToolDisplayState", () => {
  it.each([
    ["input-streaming", "running"],
    ["input-available", "running"],
    ["approval-requested", "running"],
    ["approval-responded", "running"],
    ["output-available", "done"],
    ["output-error", "failed"],
    ["output-denied", "failed"],
  ] as const)("%s → %s", (state, expected) => {
    expect(toToolDisplayState(state)).toBe(expected);
  });
});

describe("toolLabel", () => {
  const messages = getMessages();

  it("uses the contract label", () => {
    expect(toolLabel("search_products", messages)).toBe("Buscando no catálogo…");
  });

  it("falls back for unknown tools, including prototype keys", () => {
    expect(toolLabel("drop_tables", messages)).toBe("Consultando…");
    expect(toolLabel("constructor", messages)).toBe("Consultando…");
  });
});
