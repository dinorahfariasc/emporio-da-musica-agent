import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";

import { getMessages, locale } from "@/lib/i18n";
import { LocaleProvider } from "@/lib/i18n/context";
import { CHAT_WIDGET_INIT_SCRIPT } from "@/lib/chat-widget";
import { THEME_INIT_SCRIPT } from "@/lib/theme";

import "./globals.css";

// Inter is the approved typeface (DL-FE-002); weights 400/500/600/700 come from the variable font.
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const copy = getMessages(locale);

export const metadata: Metadata = {
  title: copy.app.title,
  description: copy.app.description,
};

// viewportFit "cover" lets the input bar use env(safe-area-inset-bottom) on notched phones.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // suppressHydrationWarning: the inline theme script sets data-theme before React hydrates.
    <html lang={locale} className={`${inter.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        {/* Static inline scripts (no request data), so / and /login still prerender. */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <script dangerouslySetInnerHTML={{ __html: CHAT_WIDGET_INIT_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col">
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}
