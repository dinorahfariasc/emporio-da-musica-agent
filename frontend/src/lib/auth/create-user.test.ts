import type { Pool } from "pg";
import { describe, expect, it } from "vitest";

import { createUser, PasswordTooShort, UsernameAlreadyExists } from "./create-user";

const VALID_PASSWORD = "a-fine-long-password";

class FakePool {
  users = new Map<string, { id: string; username: string; password_hash: string }>();
  nextId = 1;

  async query(sql: string, params: unknown[] = []) {
    const text = sql.trim();
    if (text.startsWith("CREATE TABLE")) return { rows: [] };
    if (text.startsWith("INSERT")) {
      const [username, passwordHash] = params as [string, string];
      if (this.users.has(username)) return { rows: [] };
      const id = `id-${this.nextId++}`;
      this.users.set(username, { id, username, password_hash: passwordHash });
      return { rows: [{ id, username }] };
    }
    throw new Error(`unexpected query: ${text}`);
  }
}

describe("createUser", () => {
  it("creates a new account and returns its id and username", async () => {
    const pool = new FakePool() as unknown as Pool;
    const user = await createUser(pool, "Demo", VALID_PASSWORD);
    expect(user.username).toBe("demo"); // lowercased
    expect(user.id).toBeTruthy();
  });

  it("fails clearly without modifying the existing row on a duplicate username", async () => {
    const fake = new FakePool();
    const pool = fake as unknown as Pool;
    await createUser(pool, "demo", VALID_PASSWORD);
    const before = fake.users.get("demo")?.password_hash;

    await expect(createUser(pool, "demo", "another-long-password")).rejects.toBeInstanceOf(
      UsernameAlreadyExists,
    );
    expect(fake.users.get("demo")?.password_hash).toBe(before);
  });

  it("rejects a password shorter than 12 characters without touching the database", async () => {
    const pool = new FakePool() as unknown as Pool;
    await expect(createUser(pool, "demo", "short")).rejects.toBeInstanceOf(PasswordTooShort);
  });
});
