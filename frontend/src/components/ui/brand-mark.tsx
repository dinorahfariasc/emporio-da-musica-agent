import { cn } from "@/lib/utils";

type BrandMarkProps = {
  className?: string;
  size?: number;
};

export function BrandMark({ className, size = 36 }: BrandMarkProps) {
  return (
    // Decorative: the adjacent heading already names Melody / the store.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/brand-mark.svg"
      alt=""
      width={size}
      height={size}
      aria-hidden
      className={cn("size-9 shrink-0 rounded-[0.65rem]", className)}
    />
  );
}
