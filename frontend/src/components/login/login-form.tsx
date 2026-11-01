"use client";

import { signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { safeCallbackPath } from "@/lib/auth/request-guards";
import { useMessages } from "@/lib/i18n/context";

export function LoginForm() {
  const messages = useMessages();
  const rawCallbackUrl = useSearchParams().get("callbackUrl");
  const callbackUrl =
    typeof window === "undefined"
      ? "/"
      : safeCallbackPath(rawCallbackUrl, window.location.origin);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(false);
    const result = await signIn("credentials", { username, password, redirect: false });
    setSubmitting(false);
    if (result?.error) {
      setError(true);
      return;
    }
    window.location.assign(callbackUrl);
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <label htmlFor="username" className="text-sm font-medium">
          {messages.login.username}
        </label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          required
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          className="flex h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-base outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm"
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor="password" className="text-sm font-medium">
          {messages.login.password}
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="flex h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-base outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 md:text-sm"
        />
      </div>
      {error && <p className="text-sm text-destructive">{messages.login.invalidCredentials}</p>}
      <Button type="submit" disabled={submitting} className="mt-1">
        {submitting ? messages.login.submitting : messages.login.submit}
      </Button>
    </form>
  );
}
