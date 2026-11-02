"use client";

import { CircleAlert, Lock } from "lucide-react";
import { signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { LoginNotice } from "@/components/login/login-notice";
import { Banner } from "@/components/ui/banner";
import { Button, Spinner } from "@/components/ui/button";
import { safeCallbackPath } from "@/lib/auth/request-guards";
import { useMessages } from "@/lib/i18n/context";

/**
 * Dev gallery only: renders a state the live form cannot reach on demand. "locked" has no
 * live trigger because auth answers lockouts and bad passwords the same way (FR-005).
 */
export type LoginPreview = "error" | "locked";

const FIELD =
  "h-[52px] w-full rounded-md border border-border bg-canvas px-4 text-base leading-6 text-primary-text outline-none placeholder:text-secondary-text focus-visible:border-2 focus-visible:border-focus focus-visible:px-[15px] aria-invalid:border-2 aria-invalid:border-error aria-invalid:bg-error-bg aria-invalid:px-[15px]";

export function LoginForm({ preview }: { preview?: LoginPreview }) {
  const messages = useMessages();
  const rawCallbackUrl = useSearchParams().get("callbackUrl");
  const callbackUrl =
    typeof window === "undefined"
      ? "/"
      : safeCallbackPath(rawCallbackUrl, window.location.origin);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(preview === "error");
  const [submitting, setSubmitting] = useState(false);
  const locked = preview === "locked";

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (preview || submitting) return;
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
    <form onSubmit={onSubmit} className="flex flex-col gap-5">
      {error ? (
        <Banner kind="error" icon={<CircleAlert />} title={messages.login.invalidCredentials}>
          {messages.login.invalidCredentialsDetail}
        </Banner>
      ) : locked ? (
        <Banner kind="warning" icon={<Lock />} title={messages.login.locked}>
          {messages.login.lockedDetail}
        </Banner>
      ) : (
        <LoginNotice />
      )}
      <div className="flex flex-col gap-1.5">
        <label htmlFor="username" className="t-label-s">
          {messages.login.username}
        </label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          required
          value={username}
          aria-invalid={error || undefined}
          placeholder={messages.login.usernamePlaceholder}
          onChange={(event) => setUsername(event.target.value)}
          className={FIELD}
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <label htmlFor="password" className="t-label-s">
          {messages.login.password}
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          aria-invalid={error || undefined}
          placeholder={messages.login.passwordPlaceholder}
          onChange={(event) => setPassword(event.target.value)}
          className={FIELD}
        />
      </div>
      <Button type="submit" disabled={locked} aria-busy={submitting || undefined} className="w-full">
        {submitting && <Spinner />}
        {submitting ? messages.login.submitting : messages.login.submit}
      </Button>
      <p className="text-center text-[13px] leading-[18px] text-secondary-text">{messages.login.noAccount}</p>
    </form>
  );
}
