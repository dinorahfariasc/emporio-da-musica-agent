// create-user CLI (FR-004, contracts/create-user-cli.md): the only way an account is created.
// Usage: DATABASE_URL_UNPOOLED=... pnpm tsx scripts/create-user.ts <username>
// Password: CREATE_USER_PASSWORD env var, or an interactive masked prompt — never argv (senior
// review #44, item J): a command-line argument lands in shell history and `ps`/process listings.
import { createInterface } from "node:readline/promises";

import { Pool } from "pg";

import { createUser, PasswordTooShort, UsernameAlreadyExists } from "../src/lib/auth/create-user";

function promptHiddenPassword(): Promise<string> {
  return new Promise((resolve) => {
    const { stdin, stdout } = process;
    stdout.write("Password: ");
    let password = "";
    const wasRaw = stdin.isTTY ? stdin.isRaw : false;
    if (stdin.isTTY) stdin.setRawMode(true);
    stdin.resume();
    stdin.setEncoding("utf8");

    const onData = (chunk: string) => {
      for (const char of chunk) {
        if (char === "\n" || char === "\r" || char === "\u0004") {
          stdin.removeListener("data", onData);
          if (stdin.isTTY) stdin.setRawMode(wasRaw);
          stdin.pause();
          stdout.write("\n");
          resolve(password);
          return;
        }
        if (char === "\u0003") {
          process.exit(1); // Ctrl-C
        } else if (char === "\u007f" || char === "\b") {
          password = password.slice(0, -1); // backspace
        } else {
          password += char;
        }
      }
    };
    stdin.on("data", onData);
  });
}

async function resolvePassword(): Promise<string> {
  if (process.env.CREATE_USER_PASSWORD) return process.env.CREATE_USER_PASSWORD;
  if (!process.stdin.isTTY) {
    // Non-interactive (e.g. piped) and no env var: read one line from stdin, unmasked.
    const rl = createInterface({ input: process.stdin });
    const line = (await rl[Symbol.asyncIterator]().next()).value as string | undefined;
    rl.close();
    return line ?? "";
  }
  return promptHiddenPassword();
}

async function main(argv: string[]): Promise<void> {
  if (argv.length < 1) {
    console.error(
      "Usage: CREATE_USER_PASSWORD=... pnpm tsx scripts/create-user.ts <username>\n" +
        "       (or omit CREATE_USER_PASSWORD to be prompted interactively)",
    );
    process.exitCode = 1;
    return;
  }
  const [username] = argv;

  const connectionString = process.env.DATABASE_URL_UNPOOLED;
  if (!connectionString) {
    console.error("DATABASE_URL_UNPOOLED is not set.");
    process.exitCode = 1;
    return;
  }

  const password = await resolvePassword();

  const pool = new Pool({ connectionString });
  try {
    const user = await createUser(pool, username, password);
    console.log(`created account ${user.id} (${user.username})`);
  } catch (error) {
    if (error instanceof UsernameAlreadyExists || error instanceof PasswordTooShort) {
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
