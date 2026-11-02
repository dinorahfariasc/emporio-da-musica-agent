import { describe, expect, it } from "vitest";

import { isPublicPage } from "@/lib/routes";

describe("isPublicPage", () => {
  it("opens only the store home", () => {
    expect(isPublicPage("/")).toBe(true);
    for (const path of ["/api/chat", "/dev/gallery", "/anything", "/api", "//"]) {
      expect(isPublicPage(path)).toBe(false);
    }
  });
});
