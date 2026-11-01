import bcrypt from "bcryptjs";
import type { Pool } from "pg";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { authorizeCredentials } from "./authorize";
import * as db from "./db";

vi.mock("./db", () => ({ findUserByUsername: vi.fn() }));

class FakePool {
  rows = new Map<string, { failed_count: number; window_start: Date }>();

  async query(sql: string, params: unknown[] = []) {
    const text = sql.trim();
    if (text.startsWith("CREATE TABLE")) return { rows: [] };
    if (text.startsWith("INSERT")) {
      const [username] = params as [string];
      const existing = this.rows.get(username);
      const failed_count = (existing?.failed_count ?? 0) + 1;
      this.rows.set(username, { failed_count, window_start: new Date() });
      return { rows: [{ failed_count }] };
    }
    if (text.startsWith("DELETE")) {
      const [username] = params as [string];
      this.rows.delete(username);
      return { rows: [] };
    }
    throw new Error(`unexpected query: ${text}`);
  }
}

function fakePool(): Pool {
  return new FakePool() as unknown as Pool;
}

beforeEach(() => {
  vi.mocked(db.findUserByUsername).mockReset();
});

describe("authorizeCredentials", () => {
  it("returns the account on a correct password", async () => {
    const passwordHash = await bcrypt.hash("correct-horse", 4);
    vi.mocked(db.findUserByUsername).mockResolvedValue({
      id: "u1",
      username: "demo",
      passwordHash,
      disabledAt: null,
    });

    const result = await authorizeCredentials(fakePool(), "demo", "correct-horse");
    expect(result).toEqual({ id: "u1", name: "demo" });
  });

  it("returns null for a wrong password", async () => {
    const passwordHash = await bcrypt.hash("correct-horse", 4);
    vi.mocked(db.findUserByUsername).mockResolvedValue({
      id: "u1",
      username: "demo",
      passwordHash,
      disabledAt: null,
    });

    expect(await authorizeCredentials(fakePool(), "demo", "wrong")).toBeNull();
  });

  it("returns null for an unknown username without ever querying a nonexistent hash", async () => {
    vi.mocked(db.findUserByUsername).mockResolvedValue(null);
    expect(await authorizeCredentials(fakePool(), "ghost", "anything")).toBeNull();
  });

  it("returns null for a disabled account even with the correct password", async () => {
    const passwordHash = await bcrypt.hash("correct-horse", 4);
    vi.mocked(db.findUserByUsername).mockResolvedValue({
      id: "u1",
      username: "demo",
      passwordHash,
      disabledAt: new Date(),
    });

    expect(await authorizeCredentials(fakePool(), "demo", "correct-horse")).toBeNull();
  });

  it("runs bcrypt.compare for both an unknown and a known username (timing parity)", async () => {
    const compareSpy = vi.spyOn(bcrypt, "compare");

    vi.mocked(db.findUserByUsername).mockResolvedValueOnce(null);
    await authorizeCredentials(fakePool(), "ghost", "anything");
    expect(compareSpy).toHaveBeenCalledTimes(1);

    const passwordHash = await bcrypt.hash("correct-horse", 4);
    vi.mocked(db.findUserByUsername).mockResolvedValueOnce({
      id: "u1",
      username: "demo",
      passwordHash,
      disabledAt: null,
    });
    await authorizeCredentials(fakePool(), "demo", "wrong");
    expect(compareSpy).toHaveBeenCalledTimes(2);

    compareSpy.mockRestore();
  });

  it("locks out after 5 failed attempts and still runs bcrypt against the dummy hash", async () => {
    const compareSpy = vi.spyOn(bcrypt, "compare");
    const pool = fakePool();
    vi.mocked(db.findUserByUsername).mockResolvedValue(null);

    for (let i = 0; i < 5; i++) {
      await authorizeCredentials(pool, "demo", "wrong");
    }
    const callsBeforeLockout = compareSpy.mock.calls.length;
    const result = await authorizeCredentials(pool, "demo", "wrong");

    expect(result).toBeNull();
    // The 6th (locked-out) attempt still ran one more bcrypt.compare, not zero.
    expect(compareSpy.mock.calls.length).toBe(callsBeforeLockout + 1);
    compareSpy.mockRestore();
  });

  it("rejects empty username or password without touching the database", async () => {
    expect(await authorizeCredentials(fakePool(), "", "x")).toBeNull();
    expect(await authorizeCredentials(fakePool(), "demo", "")).toBeNull();
    expect(db.findUserByUsername).not.toHaveBeenCalled();
  });
});
