"use client";

import { Drum, Guitar, KeyboardMusic, Music, type LucideIcon } from "lucide-react";

import { formatBrl, formatPercent } from "@/lib/format";
import { format, locale } from "@/lib/i18n";
import { useMessages } from "@/lib/i18n/context";
import type { ProductCard as Product } from "@/lib/chat/types";
import { cn } from "@/lib/utils";

// Category → thumbnail icon (presentation only; the catalog has no product images).
const CATEGORY_ICON: Record<number, LucideIcon> = {
  1: Guitar,
  2: Guitar,
  3: Drum,
  4: KeyboardMusic,
  5: Guitar,
  8: Guitar,
  9: Guitar,
};

// `.pthumb` tints c1–c4, cycled by position so neighbouring cards differ.
const THUMB_TINTS = [
  "bg-brand-subtle text-on-brand-subtle",
  "bg-info-bg text-info",
  "bg-warning-bg text-warning",
  "bg-muted text-secondary-text",
];

const BADGE_TONE: Record<string, string> = {
  in_stock: "bg-success-bg text-success",
  out_of_stock: "bg-error-bg text-error",
  coming_soon: "bg-info-bg text-info",
  discontinued: "bg-neutral-bg text-neutral",
};

type ProductCardProps = { product: Product; index?: number };

// Formatting only: price, promo price, discount and availability arrive computed from the
// backend (constitution I). The badge is hidden when availability is unknown.
export function ProductCard({ product, index = 0 }: ProductCardProps) {
  const messages = useMessages();
  const availability: Record<string, string> = messages.availability;
  const badge = Object.hasOwn(availability, product.availability)
    ? availability[product.availability]
    : null;
  const promoPrice = product.promoPriceBrl;
  const onPromo = promoPrice !== null;
  const Icon = CATEGORY_ICON[product.categoryId] ?? Music;

  return (
    <article
      aria-label={product.name}
      className="flex min-w-0 gap-3 rounded-lg border border-border bg-surface p-3 shadow-[var(--elevation-sm)]"
    >
      <div
        aria-hidden
        className={cn(
          "grid size-[72px] shrink-0 place-items-center rounded-md",
          THUMB_TINTS[index % THUMB_TINTS.length],
        )}
      >
        <Icon className="size-[30px]" strokeWidth={1.8} />
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <h3 className="text-base leading-[22px] font-semibold break-words">{product.name}</h3>
        <div className="mt-0.5 flex flex-wrap items-baseline gap-x-2 gap-y-1">
          <span className="t-price">{formatBrl(promoPrice ?? product.priceBrl, locale)}</span>
          {onPromo && (
            <>
              <span className="sr-only">
                {format(messages.product.originalPrice, { price: formatBrl(product.priceBrl, locale) })}
              </span>
              <s aria-hidden className="t-body-s text-secondary-text">
                {formatBrl(product.priceBrl, locale)}
              </s>
            </>
          )}
          {onPromo && product.discountPercent !== null && (
            <span className="rounded-full bg-brand-subtle px-2 py-0.5 text-xs leading-4 font-bold text-on-brand-subtle">
              {format(messages.product.discount, { percent: formatPercent(product.discountPercent) })}
            </span>
          )}
        </div>
        {badge && (
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs leading-4 font-semibold",
                BADGE_TONE[product.availability],
              )}
            >
              <i aria-hidden className="block size-1.5 rounded-full bg-current" />
              {badge}
            </span>
          </div>
        )}
      </div>
    </article>
  );
}
