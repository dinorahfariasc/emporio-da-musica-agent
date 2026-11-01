import { Suspense } from "react";

import { LoginForm } from "@/components/login/login-form";
import { LoginNotice } from "@/components/login/login-notice";
import { BrandMark } from "@/components/ui/brand-mark";
import { getMessages, locale } from "@/lib/i18n";

export default function LoginPage() {
  const messages = getMessages(locale);
  return (
    <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-5 px-4 py-10">
      <div className="flex flex-col items-start gap-3">
        <BrandMark className="size-12 rounded-xl" size={48} />
        <h1 className="font-heading text-3xl font-semibold tracking-tight">{messages.login.title}</h1>
      </div>
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
