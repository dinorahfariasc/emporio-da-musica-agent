# Implementation Plan: Figma branding

**Branch**: `008-figma-branding` | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: `specs/008-figma-branding/spec.md` · Epic #18 · Briefs in `docs/design/`

## Summary

Restyle the existing Next.js chat (`frontend/`) so `/` and `/login` match the Chat Melody UI
without changing stream, auth or i18n behaviour. Tokens and the store mark go in first
(`globals.css`, `public/`, fonts in `layout.tsx`). Then presentational classes on the chat
surfaces that exist on `main`. Login form, Sign out and PT/EN wait for #44 → #13.

**Palette (updated 2026-11-01, DL-FE-002):** the approved Melody UI tokens (Inter, action
`#E00B41`, brand `#FF385C` for the mark only, light + dark) replace the fallback palette
(warm paper, rosewood, brass, Fraunces + Figtree) from DL-FE-001.

## Technical Context

**Language/Version**: TypeScript 5, React 19.3, Node 24

**Primary Dependencies**: existing Next.js 16.4, Tailwind v4, shadcn/ui, `ai@7` — no new runtime
deps. Font via `next/font/google` (Inter; Fraunces + Figtree were dropped in DL-FE-002).

**Storage**: N/A

**Testing**: existing Vitest fixture suite; no colour assertions

**Target Platform**: evergreen browsers, ≥ 375 px; Vercel

**Constraints**: restyle only; Cache Components; constitution I (format, never compute); no
hardcoded copy; do not edit `src/lib/chat/*`, `src/app/api/**`, auth, backend

**Scale/Scope**: 2 routes, ~12 presentational files, tokens + a `BrandMark` component

## Constitution Check

| Principle | Check | Status |
|---|---|---|
| I. Facts from the system | Cards still only format `ProductCard` fields. Category colour is presentation. | ✅ |
| II. LLM only where it adds value | No LLM in the frontend. | ✅ N/A |
| III. Clean, traceable data | No data changes. | ✅ N/A |
| IV. Tested before done | 003 fixture tests stay green; gate run on the code PR. | ✅ |
| V. Safe and respectful | Markdown hardening, no images, no codes/JSON unchanged. | ✅ |
| VI. Simple, modular, replaceable | Tokens in CSS; no new framework. | ✅ |
| Language policy | Code/docs English; UI copy stays in the catalog. | ✅ |

## Project Structure

```text
specs/008-figma-branding/
├── spec.md
├── plan.md
└── tasks.md

frontend/
├── public/brand-mark.svg          # deleted in DL-FE-002; the mark is src/components/ui/brand-mark.tsx
├── src/app/globals.css            # brand tokens
├── src/app/layout.tsx             # fonts only (plus class hooks)
├── src/app/login/page.tsx         # placeholder layout (no form)
└── src/components/chat/*          # presentational classes
```

## Delivery slices

1. **Docs PR** (`Part of #18`): this folder + HANDOFF + `DL-FE-001` + 003 notes + backlog S13.
2. **Code PR** (current `main` surfaces): tokens, fonts, logo, empty/conversation/tools/cards/
   input/errors/header/login placeholder.
3. **Follow-up after #44 → #13** (later): login form, Sign out, PT/EN, `en.ts` chrome.

## Risks

| Risk | Mitigation |
|---|---|
| Figma tokens differ from the fallback palette | Resolved: approved tokens applied (DL-FE-002) |
| #44/#13 edit the same files | First code PR restyles `main` versions only; rebase later |
| Cache Components / prerender | Do not add `export const dynamic`; keep login notice behind Suspense |
| Tests couple to class names | Prefer roles/`data-testid`; change classes freely |
