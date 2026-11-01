"use client";

import { ProductCard } from "@/components/chat/product-card";
import type { ProductCard as Product } from "@/lib/chat/types";

type ProductCardsProps = { products: Product[] };

export function ProductCards({ products }: ProductCardsProps) {
  if (products.length === 0) return null;
  return (
    <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
