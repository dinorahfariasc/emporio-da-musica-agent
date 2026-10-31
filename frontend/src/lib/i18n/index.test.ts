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
  });

  it("has a label for every contract tool plus the fallback", () => {
    expect(Object.keys(getMessages().tools).sort()).toEqual(
      [...CONTRACT_TOOLS, "fallback"].sort(),
    );
  });
});
