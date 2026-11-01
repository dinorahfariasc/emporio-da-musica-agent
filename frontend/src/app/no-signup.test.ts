// FR-003/contracts/create-user-cli.md: no route or page may let a visitor create their own
// account — the create-user CLI is the only way. Guards against a future route accidentally
// reintroducing one (e.g. "/signup", "/register", "/api/users", "/api/signup").
import { readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const APP_DIR = dirname(fileURLToPath(import.meta.url));
const FORBIDDEN = /sign[-_]?up|register|^users$/i;

function collectRouteSegments(dir: string, segments: string[] = []): string[][] {
  const all: string[][] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (!statSync(full).isDirectory()) continue;
    const next = [...segments, entry];
    all.push(next);
    all.push(...collectRouteSegments(full, next));
  }
  return all;
}

describe("no sign-up surface", () => {
  it("has no route segment named sign-up, register, or users", () => {
    const offending = collectRouteSegments(APP_DIR).filter((segments) =>
      segments.some((segment) => FORBIDDEN.test(segment)),
    );
    expect(offending).toEqual([]);
  });
});
