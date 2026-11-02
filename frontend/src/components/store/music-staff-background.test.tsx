import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MusicStaffBackground } from "./music-staff-background";

describe("MusicStaffBackground", () => {
  it("is decorative: hidden from assistive tech, few notes, five lines per staff", () => {
    const { container } = render(<MusicStaffBackground />);
    const root = container.firstElementChild as HTMLElement;
    expect(root).toHaveAttribute("aria-hidden", "true");
    expect(root).toHaveClass("staff-bg");
    expect(root.querySelectorAll(".staff-bg__lines path")).toHaveLength(15);
    const notes = root.querySelectorAll(".staff-bg__note");
    expect(notes.length).toBeGreaterThanOrEqual(10);
    expect(notes.length).toBeLessThanOrEqual(16);
    expect(root.querySelectorAll("img, image")).toHaveLength(0);
  });
});
