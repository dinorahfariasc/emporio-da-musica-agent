import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/utils";

// Decorative store background: three gently waving staves with a few notes floating on them.
// Pure SVG + CSS (globals.css `.staff-bg`), no images, no client JS, so `/` stays static.
// Geometry lives in a 1440 × 900 box stretched over the viewport; notes are placed in % of
// that box with the same wave function, so they sit on the lines at any viewport size.

const W = 1440;
const H = 900;
const GAP = 14; // distance between staff lines (box units)
const STAVES = [
  { cy: 150, amp: 16, period: 1500, phase: 0.4 },
  { cy: 470, amp: 20, period: 1700, phase: 2.1 },
  { cy: 780, amp: 14, period: 1300, phase: 4.0 },
] as const;

function waveY(staff: number, x: number, step = 0) {
  const s = STAVES[staff];
  // `step` counts half line-gaps from the middle line (negative = higher on the staff).
  return s.cy + s.amp * Math.sin((2 * Math.PI * x) / s.period + s.phase) + (step * GAP) / 2;
}

function linePath(staff: number) {
  const points: string[] = [];
  for (let x = 0; x <= W; x += 40) points.push(`${x} ${waveY(staff, x).toFixed(1)}`);
  return `M${points.join(" L")}`;
}

const LINES = STAVES.flatMap((_, staff) =>
  [-2, -1, 0, 1, 2].map((line) => ({
    key: `${staff}-${line}`,
    d: linePath(staff),
    dy: line * GAP,
  })),
);

type Glyph = "clef" | "quarter" | "eighth" | "beamed";

// Own glyph drawings. Each viewBox puts the note head centre at (headX, headY) so it can be
// anchored on a staff line or space.
const GLYPHS: Record<Glyph, { viewBox: string; headX: number; headY: number; body: ReactNode }> = {
  clef: {
    viewBox: "0 0 40 100",
    headX: 20,
    headY: 52,
    body: (
      <path
        d="M21 94c-7 3-12-5-6-8 4-2 8 2 5 5M20 91 25 14c1-10-8-12-9-2-2 10 6 17 12 25 6 8 4 24-8 26-10 2-14-9-6-15 6-4 14 2 10 8"
        fill="none"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  quarter: {
    viewBox: "0 0 24 48",
    headX: 9,
    headY: 40,
    body: (
      <>
        <ellipse cx="9" cy="40" rx="7.5" ry="5.5" transform="rotate(-22 9 40)" fill="currentColor" />
        <rect x="14.6" y="4" width="2.4" height="35" rx="1.2" fill="currentColor" />
      </>
    ),
  },
  eighth: {
    viewBox: "0 0 30 48",
    headX: 9,
    headY: 40,
    body: (
      <>
        <ellipse cx="9" cy="40" rx="7.5" ry="5.5" transform="rotate(-22 9 40)" fill="currentColor" />
        <rect x="14.6" y="4" width="2.4" height="35" rx="1.2" fill="currentColor" />
        <path d="M16 4c1 7 12 9 11 20-.2 2-1 3-2 4 2-9-6-12-9-14Z" fill="currentColor" />
      </>
    ),
  },
  beamed: {
    viewBox: "0 0 48 48",
    headX: 9,
    headY: 40,
    body: (
      <>
        <ellipse cx="9" cy="40" rx="7.5" ry="5.5" transform="rotate(-22 9 40)" fill="currentColor" />
        <ellipse cx="35" cy="34" rx="7.5" ry="5.5" transform="rotate(-22 35 34)" fill="currentColor" />
        <rect x="14.6" y="8" width="2.4" height="31" rx="1.2" fill="currentColor" />
        <rect x="40.6" y="2" width="2.4" height="31" rx="1.2" fill="currentColor" />
        <path d="M15 8 43 2v6L15 14Z" fill="currentColor" />
      </>
    ),
  },
};

type Note = {
  glyph: Glyph;
  x: number; // box units
  staff: 0 | 1 | 2;
  step: number; // half line-gaps from the middle line
  size: number; // rendered height in px
  tone: "brand" | "neutral";
  duration: number; // s
  delay: number; // s (negative: start mid-cycle so notes move out of step)
  mobile?: boolean; // also shown below 768 px
};

const NOTES: Note[] = [
  { glyph: "clef", x: 34, staff: 0, step: 0, size: 96, tone: "neutral", duration: 11, delay: -2, mobile: true },
  { glyph: "quarter", x: 330, staff: 0, step: -1, size: 40, tone: "brand", duration: 7, delay: -1, mobile: true },
  { glyph: "beamed", x: 620, staff: 0, step: 1, size: 40, tone: "neutral", duration: 9, delay: -4 },
  { glyph: "eighth", x: 960, staff: 0, step: -3, size: 40, tone: "brand", duration: 8, delay: -6 },
  { glyph: "quarter", x: 1280, staff: 0, step: 2, size: 40, tone: "neutral", duration: 10, delay: -3, mobile: true },
  { glyph: "clef", x: 34, staff: 1, step: 0, size: 104, tone: "neutral", duration: 12, delay: -7 },
  { glyph: "eighth", x: 240, staff: 1, step: 2, size: 42, tone: "neutral", duration: 9, delay: -2, mobile: true },
  { glyph: "beamed", x: 520, staff: 1, step: -2, size: 44, tone: "brand", duration: 11, delay: -5 },
  { glyph: "quarter", x: 860, staff: 1, step: 0, size: 40, tone: "brand", duration: 6.5, delay: -3 },
  { glyph: "eighth", x: 1180, staff: 1, step: -1, size: 42, tone: "brand", duration: 8.5, delay: -1, mobile: true },
  { glyph: "clef", x: 34, staff: 2, step: 0, size: 92, tone: "neutral", duration: 10, delay: -5, mobile: true },
  { glyph: "beamed", x: 400, staff: 2, step: 1, size: 40, tone: "brand", duration: 10.5, delay: -8, mobile: true },
  { glyph: "quarter", x: 760, staff: 2, step: -2, size: 38, tone: "neutral", duration: 7.5, delay: -2 },
  { glyph: "eighth", x: 1100, staff: 2, step: 2, size: 40, tone: "brand", duration: 9.5, delay: -6 },
];

export function MusicStaffBackground({ className }: { className?: string }) {
  return (
    <div aria-hidden className={cn("staff-bg", className)}>
      <svg className="staff-bg__lines" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" focusable="false">
        {LINES.map((line) => (
          <path key={line.key} d={line.d} transform={`translate(0 ${line.dy})`} vectorEffect="non-scaling-stroke" />
        ))}
      </svg>
      {NOTES.map((note, index) => {
        const glyph = GLYPHS[note.glyph];
        const [, , vw, vh] = glyph.viewBox.split(" ").map(Number);
        const width = (note.size * vw) / vh;
        const style = {
          left: `${(note.x / W) * 100}%`,
          top: `${(waveY(note.staff, note.x, note.step) / H) * 100}%`,
          width,
          height: note.size,
          marginLeft: -(glyph.headX / vw) * width,
          marginTop: -(glyph.headY / vh) * note.size,
          "--staff-note-duration": `${note.duration}s`,
          "--staff-note-delay": `${note.delay}s`,
          "--staff-note-tilt": `${index % 2 ? -4 : 4}deg`,
        } as CSSProperties;
        return (
          <span
            key={index}
            className={cn("staff-bg__note", `staff-bg__note--${note.tone}`, !note.mobile && "max-md:hidden")}
            style={style}
          >
            <svg viewBox={glyph.viewBox} width="100%" height="100%" overflow="visible" focusable="false">
              {glyph.body}
            </svg>
          </span>
        );
      })}
    </div>
  );
}
