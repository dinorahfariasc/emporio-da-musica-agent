// Server-safe: client components read copy with `useMessages` from "./context".
import { en } from "./en";
import { ptBR, type Messages } from "./pt-BR";

export type { Messages };

export type LocaleCode = "pt-BR" | "en";

// pt-BR first: the site and the agent persona default to Portuguese.
export const locale: LocaleCode = "pt-BR";

export const SUPPORTED_LOCALES: readonly LocaleCode[] = ["pt-BR", "en"];

const catalogs: Record<LocaleCode, Messages> = { "pt-BR": ptBR, en };

export function getMessages(target: string = locale): Messages {
  return Object.hasOwn(catalogs, target) ? catalogs[target as LocaleCode] : ptBR;
}

export function format(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    Object.hasOwn(vars, key) ? String(vars[key]) : match,
  );
}
