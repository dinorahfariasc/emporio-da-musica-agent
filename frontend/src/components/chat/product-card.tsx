"use client";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { formatBrl, formatPercent } from "@/lib/format";
import { format, locale } from "@/lib/i18n";
import { useMessages } from "@/lib/i18n/context";
import type { ProductCard as Product } from "@/lib/chat/types";

type ProductCardProps = { product: Product };

// Formatting only: every value comes computed from the backend (constitution I).
export function ProductCard({ product }: ProductCardProps) {
  const messages = useMessages();
  const availability: Record<string, string> = messages.availability;
  const badge = Object.hasOwn(availability, product.availability)
    ? availability[product.availability]
    : null;
  const promoPrice = product.promoPriceBrl;
  const onPromo = promoPrice !== null;

  return (
    <Card size="sm" role="article" aria-label={product.name} className="min-w-0 gap-2 px-3">
      <h3 className="text-sm leading-snug font-medium break-words">{product.name}</h3>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <span className="text-base font-semibold">
          {formatBrl(promoPrice ?? product.priceBrl, locale)}
        </span>
        {onPromo && (
          <>
            <span className="sr-only">
              {format(messages.product.originalPrice, { price: formatBrl(product.priceBrl, locale) })}
            </span>
            <s aria-hidden className="text-xs text-muted-foreground">
              {formatBrl(product.priceBrl, locale)}
            </s>
          </>
        )}
        {onPromo && product.discountPercent !== null && (
          <Badge variant="secondary">
            {format(messages.product.discount, { percent: formatPercent(product.discountPercent) })}
          </Badge>
        )}
      </div>
      {badge && (
        <Badge variant="outline" className="self-start">
          {badge}
        </Badge>
      )}
    </Card>
  );
}
