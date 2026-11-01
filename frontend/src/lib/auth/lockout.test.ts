import type { Pool } from "pg";
import { describe, expect, it } from "vitest";

import { clearAttempts, isLockedOut, recordFailedAttempt } from "./lockout";

// A minimal in-memory stand-in for `pg.Pool` so lockout logic is tested without a real database.
class FakePool {
  rows = new Map<string, { failed_count: number; window_start: Date }>();

  async query(sql: string, params: unknown[] = []) {
    const text = sql.trim();
    if (text.startsWith("CREATE TABLE")) return { rows: [] };
    const username = params[0] as string;
    if (text.startsWith("SELECT")) {
      const row = this.rows.get(username);
      return { rows: row ? [row] : [] };
    }
    if (text.startsWith("INSERT")) {
      this.rows.set(username, { failed_count: 1, window_start: params[1] as Date });
      return { rows: [] };
    }
    if (text.startsWith("UPDATE")) {
      const row = this.rows.get(username);
      if (row) row.failed_count += 1;
      return { rows: [] };
    }
    if (text.startsWith("DELETE")) {
      this.rows.delete(username);
      return { rows: [] };
    }
    throw new Error(`unexpected query: ${text}`);
  }
}

function fakeClock(ms: number) {
  return () => new Date(ms);
}

describe("sign-in lockout", () => {
  it("locks out after 5 failures within 15 minutes", async () => {
    const pool = new FakePool() as unknown as Pool;
    const now = fakeClock(0);
    for (let i = 0; i < 5; i++) {
      expect(await isLockedOut(pool, "demo", now)).toBe(false);
      await recordFailedAttempt(pool, "demo", now);
    }
    expect(await isLockedOut(pool, "demo", now)).toBe(true);
  });

  it("clears the lock after a successful login", async () => {
    const pool = new FakePool() as unknown as Pool;
    const now = fakeClock(0);
    for (let i = 0; i < 5; i++) await recordFailedAttempt(pool, "demo", now);
    expect(await isLockedOut(pool, "demo", now)).toBe(true);

    await clearAttempts(pool, "demo");
    expect(await isLockedOut(pool, "demo", now)).toBe(false);
  });

  it("resets the window after 15 minutes", async () => {
    const pool = new FakePool() as unknown as Pool;
    const start = fakeClock(0);
    for (let i = 0; i < 5; i++) await recordFailedAttempt(pool, "demo", start);
    expect(await isLockedOut(pool, "demo", start)).toBe(true);

    const later = fakeClock(16 * 60 * 1000);
    expect(await isLockedOut(pool, "demo", later)).toBe(false);
  });

  it("username lookup is case-insensitive", async () => {
    const pool = new FakePool() as unknown as Pool;
    const now = fakeClock(0);
    for (let i = 0; i < 5; i++) await recordFailedAttempt(pool, "Demo", now);
    expect(await isLockedOut(pool, "demo", now)).toBe(true);
  });
});
