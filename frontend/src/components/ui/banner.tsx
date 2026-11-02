import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export type BannerKind = "error" | "warning" | "info" | "neutral";

const KIND: Record<BannerKind, string> = {
  error: "bg-error-bg [&_[data-slot=banner-accent]]:text-error",
  warning: "bg-warning-bg [&_[data-slot=banner-accent]]:text-warning",
  info: "bg-info-bg [&_[data-slot=banner-accent]]:text-info",
  neutral: "bg-subtle [&_[data-slot=banner-accent]]:text-primary-text",
};

type BannerProps = {
  kind: BannerKind;
  icon: ReactNode;
  title: ReactNode;
  children?: ReactNode;
  actions?: ReactNode;
  className?: string;
  "data-testid"?: string;
};

// `.banner` (components.css): icon 24, title 600 15/22 in the status colour, description
// 400 14/20 in text/primary, actions 12 px below. Announced politely (role="status").
export function Banner({ kind, icon, title, children, actions, className, ...rest }: BannerProps) {
  return (
    <div
      role="status"
      data-kind={kind}
      className={cn("flex items-start gap-3 rounded-lg p-4", KIND[kind], className)}
      {...rest}
    >
      <span data-slot="banner-accent" aria-hidden className="size-6 shrink-0 [&_svg]:size-6">
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <p data-slot="banner-accent" className="text-[15px] leading-[22px] font-semibold">
          {title}
        </p>
        {children && <div className="t-body-s mt-0.5 text-primary-text">{children}</div>}
        {actions && <div className="mt-3 flex flex-wrap gap-2">{actions}</div>}
      </div>
    </div>
  );
}
