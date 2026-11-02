"use client";

import { ProductCard } from "@/components/chat/product-card";
import type { ProductCard as Product } from "@/lib/chat/types";

type ProductCardsProps = { products: Product[] };

// `.cards`: one column on mobile, two on desktop (`.cards.two`).
export function ProductCards({ products }: ProductCardsProps) {
  if (products.length === 0) return null;
  return (
    <div className="grid grid-cols-1 gap-3 @3xl:grid-cols-2">
      {products.map((product, index) => (
        <ProductCard key={product.id} product={product} index={index} />
      ))}
    </div>
  );
}
