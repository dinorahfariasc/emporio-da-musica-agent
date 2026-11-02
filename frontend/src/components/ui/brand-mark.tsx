import { Music } from "lucide-react";

import { cn } from "@/lib/utils";

type BrandMarkProps = { className?: string; iconClassName?: string };

// Store mark (design Foundations › Logo): a music note in a 36 px rounded square, radius 12, in
// accent/brand #FF385C. Decorative only: the adjacent store name names it.
export function BrandMark({ className, iconClassName }: BrandMarkProps) {
  return (
    <span
      aria-hidden
      className={cn(
        "grid size-9 shrink-0 place-items-center rounded-md bg-brand text-white",
        className,
      )}
    >
      <Music className={cn("size-5", iconClassName)} strokeWidth={2.2} />
    </span>
  );
}

type LogoProps = {
  name: string;
  subtitle?: string;
  className?: string;
  nameClassName?: string;
  subtitleClassName?: string;
};

// `.logo`: mark + store name (700 17/20, accent/brand) + optional subtitle (500 12/16, secondary).
export function Logo({ name, subtitle, className, nameClassName, subtitleClassName }: LogoProps) {
  return (
    <div className={cn("flex min-w-0 items-center gap-2.5", className)}>
      <BrandMark />
      <div className="min-w-0">
        <p
          className={cn(
            "truncate text-[17px] leading-5 font-bold tracking-[-0.01em] text-brand",
            nameClassName,
          )}
        >
          {name}
        </p>
        {subtitle && (
          <p className={cn("t-caption truncate text-secondary-text", subtitleClassName)}>
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}

type MelodyAvatarProps = { className?: string; iconClassName?: string };

// `.avatar`: 32 px circle, accent/subtle with the note in accent/on-subtle.
export function MelodyAvatar({ className, iconClassName }: MelodyAvatarProps) {
  return (
    <span
      aria-hidden
      className={cn(
        "grid size-8 shrink-0 place-items-center rounded-full bg-brand-subtle text-on-brand-subtle",
        className,
      )}
    >
      <Music className={cn("size-4", iconClassName)} strokeWidth={2.2} />
    </span>
  );
}
