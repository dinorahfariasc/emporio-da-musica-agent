import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProductCards } from "@/components/chat/product-cards";
import type { ChatDataParts, ProductCard } from "@/lib/chat/types";
import { assembleMessage } from "@/test/fixtures";


async function fixtureProducts(): Promise<ProductCard[]> {
  const message = await assembleMessage("tool-products");
  const part = message.parts.find((p) => p.type === "data-products");
  return (part as { data: ChatDataParts["products"] }).data.products;
}

const promo: ProductCard = {
  id: 1,
  name: "Pedal Overdrive Clássico",
  categoryId: 3,
  priceBrl: 200,
  promoPriceBrl: 160,
  discountPercent: 20,
  availability: "in_stock",
};

describe("ProductCards", () => {
  it("shows the fixture products with exact prices and availability", async () => {
    render(<ProductCards products={await fixtureProducts()} />);
    const cards = screen.getAllByRole("article");
    expect(cards).toHaveLength(2);
    expect(within(cards[0]).getByText("Tagima Woodstock Dreadnought Natural")).toBeInTheDocument();
    expect(within(cards[0]).getByText("R$ 899,00")).toBeInTheDocument();
    expect(within(cards[1]).getByText("Yamaha F310 Aço Natural")).toBeInTheDocument();
    expect(within(cards[1]).getByText("R$ 699,90")).toBeInTheDocument();
    expect(screen.getAllByText("Em estoque")).toHaveLength(2);
  });

  it("shows the promo price, the struck original price and the discount", () => {
    const { container } = render(<ProductCards products={[promo]} />);
    expect(screen.getByText("R$ 160,00")).toBeInTheDocument();
    const original = container.querySelector("s");
    expect(original).toHaveTextContent("R$ 200,00");
    expect(screen.getByText("-20%")).toBeInTheDocument();
  });

  it("hides the badge for an unknown availability", () => {
    const odd = { ...promo, availability: "backorder" } as unknown as ProductCard;
    render(<ProductCards products={[odd]} />);
    for (const label of ["Em estoque", "Esgotado", "Em breve", "Fora de linha", "backorder"]) {
      expect(screen.queryByText(label)).toBeNull();
    }
  });

  it("renders nothing for an empty list", () => {
    const { container } = render(<ProductCards products={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("lets a long name wrap", () => {
    const long = { ...promo, name: "Guitarra ".repeat(30).trim() };
    render(<ProductCards products={[long]} />);
    expect(screen.getByText(long.name).className).toMatch(/break-words/);
  });
});
