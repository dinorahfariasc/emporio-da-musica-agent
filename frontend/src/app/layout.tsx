import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { locale } from "@/lib/i18n";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Melody · Empório da Música",
  description: "Assistente virtual da Empório da Música",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang={locale}
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
