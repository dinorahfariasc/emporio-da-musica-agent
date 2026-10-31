import { describe, expect, it } from "vitest";

import { formatBrl, formatPercent } from "@/lib/format";

const plain = (s: string) => s.replace(/ /g, " ");

describe("format", () => {
  it("formats BRL with the locale", () => {
    expect(plain(formatBrl(899, "pt-BR"))).toBe("R$ 899,00");
    expect(plain(formatBrl(699.9, "pt-BR"))).toBe("R$ 699,90");
  });

  it("formats an already-percentage value as an integer", () => {
    expect(formatPercent(20)).toBe("20%");
  });
});
