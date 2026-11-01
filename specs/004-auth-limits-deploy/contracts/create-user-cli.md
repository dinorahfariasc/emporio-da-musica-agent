# Contract: `create-user` CLI (FR-004)

A Node script, `frontend/scripts/create-user.ts`, run locally or from any machine that has the
production `DATABASE_URL_UNPOOLED` value (never committed; the user holds it, same convention as
every other production secret in this project — see `docs/HANDOFF.md` §5).

## Usage

```sh
cd frontend
# password prompted interactively (masked), or via CREATE_USER_PASSWORD
DATABASE_URL_UNPOOLED="postgres://..." pnpm tsx scripts/create-user.ts <username>
```

- `<username>`: lowercased before storage; must be non-empty and not already present.
- The password is **never a CLI argument** (it would land in shell history and any `ps`/process
  listing on the machine running it). It comes from the `CREATE_USER_PASSWORD` env var if set,
  otherwise an interactive masked prompt (or one line read from stdin if not a TTY); it must be at
  least 12 characters.
- The password is hashed with `bcryptjs` before storage; never logged, never echoed back, never
  written to any file.

## Behavior

| Case | Result |
|---|---|
| Username does not exist yet | Inserts a row into `users`; prints the new account's `id` and username (never the hash) to stdout; exits 0. |
| Username already exists | Exits non-zero with a clear "username already exists" message; does **not** update the password (re-provisioning is a conscious separate action, not a silent side effect of re-running the same command — avoids accidentally resetting a password because of a typo'd re-run). |
| Password shorter than 12 characters | Exits non-zero with a clear message; nothing is written. |
| `DATABASE_URL_UNPOOLED` not set | Exits non-zero immediately with a clear message; never falls back to a default/local connection string for a command that touches production data. |
| No username argument | Prints usage and exits non-zero. |

## Explicitly out of scope

- No password reset / update subcommand (spec Assumptions: no self-service; the user can delete
  and re-create a row directly in Neon's console for the rare case a password needs changing — not
  worth a second CLI command at this scale).
- No bulk-import mode (one or a handful of accounts, created one at a time).
- No public-facing equivalent (no `/api/users` route, no sign-up page) — this is the *only* way an
  account is created, satisfying FR-003/FR-004 together.
