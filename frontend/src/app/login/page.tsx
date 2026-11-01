import { Suspense } from "react";

import { LoginForm } from "@/components/login/login-form";
import { LoginNotice } from "@/components/login/login-notice";
import { getMessages, locale } from "@/lib/i18n";

export default function LoginPage() {
  const messages = getMessages(locale);
  return (
    <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-4 px-4 py-8">
      <h1 className="text-2xl font-semibold">{messages.login.title}</h1>
      {/* useSearchParams needs a Suspense boundary under Cache Components. */}
      <Suspense>
        <LoginNotice />
      </Suspense>
      <Suspense>
        <LoginForm />
      </Suspense>
    </main>
  );
}
