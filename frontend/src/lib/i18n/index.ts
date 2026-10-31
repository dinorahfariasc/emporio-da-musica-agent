// Server-safe: client components read copy with `useMessages` from "./context".
import { ptBR, type Messages } from "./pt-BR";

export type { Messages };

export const locale = "pt-BR";

const catalogs: Record<string, Messages> = { "pt-BR": ptBR };

export function getMessages(target: string = locale): Messages {
  return catalogs[target] ?? ptBR;
}

export function format(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    Object.hasOwn(vars, key) ? String(vars[key]) : match,
  );
}
