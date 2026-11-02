// EXEMPLO — sample data for the DEV-only gallery. Not real products, prices or orders; the
// values only exercise formatting (the live UI shows what the backend sends, as is).
import type { ChatMessage, ProductCard } from "@/lib/chat/types";

type Part = ChatMessage["parts"][number];

let seq = 0;
const id = (prefix: string) => `${prefix}-exemplo-${++seq}`;

export function user(text: string): ChatMessage {
  return { id: id("u"), role: "user", parts: [{ type: "text", text }] };
}

export function melody(...parts: Part[]): ChatMessage {
  return { id: id("a"), role: "assistant", parts };
}

export function text(value: string, streaming = false): Part {
  return { type: "text", text: value, state: streaming ? "streaming" : "done" };
}

export function tool(name: string, state: "running" | "done" | "failed"): Part {
  const base = { type: `tool-${name}`, toolCallId: id("call"), input: {} };
  const part =
    state === "done"
      ? { ...base, state: "output-available", output: {} }
      : state === "failed"
        ? { ...base, state: "output-error", errorText: "" }
        : { ...base, state: "input-available" };
  return part as Part;
}

export function products(items: ProductCard[]): Part {
  return { type: "data-products", id: id("products"), data: { products: items } };
}

const card = (
  name: string,
  priceBrl: number,
  availability: ProductCard["availability"],
  promo?: { promoPriceBrl: number; discountPercent: number },
): ProductCard => ({
  id: ++seq,
  name,
  categoryId: 5,
  priceBrl,
  promoPriceBrl: promo?.promoPriceBrl ?? null,
  discountPercent: promo?.discountPercent ?? null,
  availability,
});

export const CARDS = [
  card("Violão Takamine GD20 Natural", 999.9, "in_stock", { promoPriceBrl: 849.9, discountPercent: 15 }),
  card("Violão Yamaha C40 Clássico", 699, "out_of_stock"),
  card("Violão Giannini GF-1D Folk", 559.9, "coming_soon"),
  card("Violão Di Giorgio Estudante", 389, "discontinued"),
];

export const Q = "Quais violões vocês têm até R$ 1.000?";
export const ANSWER =
  "Encontrei **3 violões até R$ 1.000** no catálogo. O Takamine GD20 está em promoção: **15% de desconto**.\n\nQuer que eu compare os modelos ou veja as formas de pagamento?";
export const ANSWER_DESKTOP =
  "Encontrei **4 violões até R$ 1.000**. Destaques:\n\n- **Takamine GD20** com 15% de desconto\n- **Yamaha C40** está esgotado no momento\n\nVeja as [políticas de troca](https://example.com/politicas) antes de comprar.";
export const HANDOFF =
  "Pronto! Registrei sua solicitação de atendimento humano.\n\n- **Protocolo:** EMP-2026-004812 `EXEMPLO`\n- **Motivo:** produto com defeito, pedido #10234\n\nNossa equipe vai responder no e-mail cadastrado em até **1 dia útil**.";
