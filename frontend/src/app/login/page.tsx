import Link from "next/link";
import { Suspense } from "react";

import { LoginNotice } from "@/components/login/login-notice";
import { getMessages, locale } from "@/lib/i18n";

// Placeholder until auth (#10) replaces it behind the same path and query.
export default function LoginPage() {
  const messages = getMessages(locale);
  return (
    <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-4 px-4 py-8">
      <h1 className="text-2xl font-semibold">{messages.login.title}</h1>
      {/* useSearchParams needs a Suspense boundary under Cache Components. */}
      <Suspense>
        <LoginNotice />
      </Suspense>
      <p className="text-sm text-muted-foreground">{messages.login.placeholder}</p>
      <Link href="/" className="inline-flex min-h-11 items-center text-sm font-medium text-primary underline underline-offset-3">
        {messages.login.backToChat}
      </Link>
    </main>
  );
}
