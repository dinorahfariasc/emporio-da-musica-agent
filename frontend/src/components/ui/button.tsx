import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"

// Variants and sizes follow the design handoff `components.css` (.btn, .btn.sm, .icon-btn):
// default (primary) / secondary / ghost × default, pressed (:active), focus, disabled, loading.
const buttonVariants = cva(
  "group/button inline-flex shrink-0 cursor-pointer items-center justify-center gap-2 border border-transparent font-semibold whitespace-nowrap transition-colors select-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus disabled:pointer-events-none data-disabled:pointer-events-none [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-action text-on-accent active:bg-action-pressed disabled:bg-muted disabled:text-disabled",
        secondary:
          "border-strong bg-canvas text-primary-text active:bg-subtle disabled:border-transparent disabled:bg-muted disabled:text-disabled",
        ghost:
          "bg-transparent text-primary-text underline underline-offset-3 active:bg-subtle disabled:bg-muted disabled:text-disabled disabled:no-underline",
        outline:
          "border-border bg-canvas text-primary-text active:bg-subtle disabled:bg-muted disabled:text-disabled",
        destructive: "bg-error-bg text-error active:bg-error-bg/80",
        link: "text-link underline-offset-4 hover:underline",
      },
      size: {
        default: "h-12 rounded-md px-6 text-base leading-5 [&_svg:not([class*='size-'])]:size-[18px]",
        sm: "h-11 rounded-md px-4 text-sm leading-5 [&_svg:not([class*='size-'])]:size-4",
        lg: "h-12 rounded-md px-6 text-base leading-5",
        xs: "h-8 rounded-sm px-2 text-xs",
        icon: "size-11 rounded-full",
        "icon-xs": "size-6 rounded-full",
        "icon-sm": "size-8 rounded-full",
        "icon-lg": "size-11 rounded-full",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

/** Loading spinner from components.css `.spin` (inherits the button's text colour). */
function Spinner({ className }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block size-[18px] animate-spin rounded-full border-[2.5px] border-current border-r-transparent opacity-90 motion-reduce:animate-none",
        className
      )}
    />
  )
}

export { Button, Spinner, buttonVariants }
