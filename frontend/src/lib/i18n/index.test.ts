import { describe, expect, it } from "vitest";

import { format, getMessages } from "@/lib/i18n";

const CONTRACT_TOOLS = [
  "search_products",
  "get_product",
  "find_similar_products",
  "get_active_promotions",
  "calculate_payment_options",
  "get_order_status",
  "search_policies",
  "get_store_info",
  "check_return_eligibility",
  "request_return",
  "register_complaint",
  "handoff_to_human",
] as const;

describe("i18n", () => {
  it("interpolates named variables and keeps unknown ones", () => {
    expect(format("Você poderá enviar em {seconds}s", { seconds: 30 })).toBe(
      "Você poderá enviar em 30s",
    );
    expect(format("{a} e {b}", { a: 1 })).toBe("1 e {b}");
    expect(format("{toString}", {})).toBe("{toString}");
  });

  it("has a label for every contract tool plus the fallback", () => {
    expect(Object.keys(getMessages().tools).sort()).toEqual(
      [...CONTRACT_TOOLS, "fallback"].sort(),
    );
  });

  it("has a done label for every tool label, in both locales", () => {
    for (const locale of ["pt-BR", "en"] as const) {
      const catalog = getMessages(locale);
      expect(Object.keys(catalog.toolsDone).sort()).toEqual(Object.keys(catalog.tools).sort());
    }
  });

  it("keeps the English catalog in step with pt-BR", () => {
    const keys = (value: unknown, prefix = ""): string[] =>
      value && typeof value === "object"
        ? Object.entries(value).flatMap(([k, v]) => keys(v, `${prefix}${k}.`))
        : [prefix];
    expect(keys(getMessages("en")).sort()).toEqual(keys(getMessages("pt-BR")).sort());
  });
});
