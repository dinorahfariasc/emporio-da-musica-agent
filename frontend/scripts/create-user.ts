// create-user CLI (FR-004, contracts/create-user-cli.md): the only way an account is created.
// Usage: DATABASE_URL_UNPOOLED=... pnpm tsx scripts/create-user.ts <username> <password>
import { Pool } from "pg";

import { createUser, UsernameAlreadyExists } from "../src/lib/auth/create-user";

async function main(argv: string[]): Promise<void> {
  if (argv.length < 2) {
    console.error("Usage: pnpm tsx scripts/create-user.ts <username> <password>");
    process.exitCode = 1;
    return;
  }
  const [username, password] = argv;

  const connectionString = process.env.DATABASE_URL_UNPOOLED;
  if (!connectionString) {
    console.error("DATABASE_URL_UNPOOLED is not set.");
    process.exitCode = 1;
    return;
  }

  const pool = new Pool({ connectionString });
  try {
    const user = await createUser(pool, username, password);
    console.log(`created account ${user.id} (${user.username})`);
  } catch (error) {
    if (error instanceof UsernameAlreadyExists) {
      console.error(error.message);
      process.exitCode = 1;
      return;
    }
    throw error;
  } finally {
    await pool.end();
  }
}

main(process.argv.slice(2));
