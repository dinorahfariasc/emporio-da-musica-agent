import { ptBR, type Messages } from "./pt-BR";

export type { Messages };
export { MessagesContext, useMessages } from "./context";

export const locale = "pt-BR";

const catalogs: Record<string, Messages> = { "pt-BR": ptBR };

export function getMessages(target: string = locale): Messages {
  return catalogs[target] ?? ptBR;
}

export function format(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in vars ? String(vars[key]) : match,
  );
}
