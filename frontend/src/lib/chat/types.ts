import type { UIMessage } from "ai";

// Mirrors the chat stream contract (docs/contracts/chat-stream.md).

export type Availability = "in_stock" | "out_of_stock" | "coming_soon" | "discontinued";

// Nullable fields are always present.
export type ProductCard = {
  id: number;
  name: string;
  categoryId: number;
  priceBrl: number;
  promoPriceBrl: number | null;
  discountPercent: number | null;
  availability: Availability;
};

export type ChatDataParts = { products: { products: ProductCard[] } };

export type ChatMetadata = {
  route: { intent: string; confidence: number; router: "jev" | "haiku" | "fake" };
  model: string;
  usage: { inputTokens: number; outputTokens: number };
};

export type ChatMessage = UIMessage<ChatMetadata, ChatDataParts>;
