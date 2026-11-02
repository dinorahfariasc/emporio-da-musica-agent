"use client";

import type { ChatStatus } from "ai";
import { useSearchParams } from "next/navigation";
import type { ReactNode } from "react";

import { ChatError } from "@/components/chat/chat-error";
import type { InputLock } from "@/components/chat/chat-input";
import { ChatView } from "@/components/chat/chat-view";
import { StoppedNotice } from "@/components/chat/stopped-notice";
import { LoginForm, type LoginPreview } from "@/components/login/login-form";
import { LoginScreen } from "@/components/login/login-screen";
import { SignInPrompt } from "@/components/store/chat-widget";
import { StoreSections } from "@/components/store/store-sections";
import { StoreShell } from "@/components/store/store-shell";
import type { ChatMessage } from "@/lib/chat/types";
import { useMessages } from "@/lib/i18n/context";

import { ANSWER, ANSWER_DESKTOP, CARDS, HANDOFF, Q, melody, products, text, tool, user } from "./examples";

type ChatScreen = {
  kind: "chat";
  messages: ChatMessage[];
  status?: ChatStatus;
  typing?: boolean;
  banner?: ReactNode;
  footer?: ReactNode;
  lock?: InputLock;
};
type LoginScreenDef = { kind: "login"; preview?: LoginPreview };
type WidgetSignInScreen = { kind: "widget-signin" };
type Screen = ChatScreen | LoginScreenDef | WidgetSignInScreen;

const noop = () => {};

function useScreens(): Record<string, Screen> {
  const copy = useMessages();
  return {
    "chat-empty": { kind: "chat", messages: [] },
    "chat-typing": { kind: "chat", messages: [user(Q)], status: "submitted", typing: true },
    "chat-streaming": {
      kind: "chat",
      status: "streaming",
      messages: [
        user(Q),
        melody(
          tool("search_products", "done"),
          tool("get_active_promotions", "running"),
          text("Encontrei **3 violões até R$ 1.000** no catálogo. O Takamine GD20", true),
        ),
      ],
    },
    "chat-conversa": {
      kind: "chat",
      messages: [
        user(Q),
        melody(
          tool("search_products", "done"),
          tool("get_active_promotions", "done"),
          text(ANSWER),
          products(CARDS.slice(0, 3)),
        ),
      ],
    },
    "chat-conversa-desktop": {
      kind: "chat",
      messages: [
        user("Oi! Vocês têm violão para iniciante?"),
        melody(
          text("Temos sim! Para começar, os mais procurados são violões de cordas de nylon. Qual é o seu orçamento?"),
        ),
        user(Q),
        melody(
          tool("search_products", "done"),
          tool("get_active_promotions", "done"),
          text(ANSWER_DESKTOP),
          products(CARDS),
        ),
      ],
    },
    "chat-stopped": {
      kind: "chat",
      messages: [
        user(Q),
        melody(
          tool("search_products", "done"),
          text("Encontrei **3 violões até R$ 1.000** no catálogo. O Takamine GD20 está em"),
        ),
      ],
      footer: <StoppedNotice />,
    },
    "chat-rate-limit": {
      kind: "chat",
      messages: [user("Posso parcelar em 12x?")],
      banner: (
        <ChatError
          error={{ kind: "rate_limited", message: "", retryAfterSeconds: 42 }}
          onRetry={noop}
          onExpire={noop}
        />
      ),
      lock: { reason: "rate_limited", seconds: 42 },
    },
    "chat-rate-ready": {
      kind: "chat",
      messages: [user("Posso parcelar em 12x?")],
      banner: (
        <ChatError
          error={{ kind: "rate_limited", message: "", retryAfterSeconds: 0 }}
          onRetry={noop}
          onExpire={noop}
        />
      ),
    },
    "chat-budget": {
      kind: "chat",
      messages: [user("Qual o prazo de entrega para Campo Grande?")],
      banner: (
        <ChatError error={{ kind: "budget_exhausted", message: "" }} onRetry={noop} onExpire={noop} />
      ),
      lock: { reason: "budget" },
    },
    "chat-erro-500": {
      kind: "chat",
      messages: [user("Qual o horário de funcionamento?")],
      banner: (
        <ChatError
          error={{ kind: "retryable", message: copy.errors.fallback }}
          onRetry={noop}
          onExpire={noop}
        />
      ),
    },
    "chat-stream-falhou": {
      kind: "chat",
      messages: [
        user("Como faço para devolver um produto?"),
        melody(
          tool("search_policies", "done"),
          text(
            "Você pode devolver em até **7 dias** após o recebimento, desde que o produto esteja na embalagem original. Para iniciar,",
          ),
        ),
      ],
      footer: (
        <ChatError
          variant="dropped"
          error={{ kind: "retryable", message: copy.errors.fallback }}
          onRetry={noop}
          onExpire={noop}
        />
      ),
    },
    "chat-handoff": {
      kind: "chat",
      messages: [
        user("Quero falar com uma pessoa sobre meu pedido com defeito."),
        melody(
          tool("check_return_eligibility", "done"),
          tool("handoff_to_human", "done"),
          text(HANDOFF),
        ),
      ],
    },
    "chat-tool-failed": {
      kind: "chat",
      messages: [
        user("Cadê meu pedido #10234?"),
        melody(
          tool("get_order_status", "failed"),
          text("Não consegui acessar os pedidos neste momento. Quer tentar de novo em alguns minutos?"),
        ),
      ],
    },
    // Store page with the widget showing the signed-out prompt. Any chat screen also renders
    // inside the store widget with `&frame=widget`.
    "widget-signin": { kind: "widget-signin" },
    "login-normal": { kind: "login" },
    "login-error": { kind: "login", preview: "error" },
    "login-locked": { kind: "login", preview: "locked" },
    // login-expired: open with `&reason=expired` (the live trigger, read from the URL).
    "login-expired": { kind: "login" },
  };
}

function Index({ names }: { names: string[] }) {
  return (
    <main className="mx-auto w-full max-w-(--size-content-max) p-6">
      <h1 className="t-title-m">Dev gallery · EXEMPLO</h1>
      <ul className="mt-4 flex flex-col gap-2">
        {names.map((name) => (
          <li key={name}>
            <a
              className="text-link underline"
              href={`?screen=${name}${name === "login-expired" ? "&reason=expired" : ""}`}
            >
              {name}
            </a>
          </li>
        ))}
      </ul>
    </main>
  );
}

export function Gallery() {
  const screens = useScreens();
  const params = useSearchParams();
  const name = params.get("screen") ?? "";
  const inWidget = params.get("frame") === "widget";
  const screen = Object.hasOwn(screens, name) ? screens[name] : null;

  if (!screen) return <Index names={Object.keys(screens)} />;

  const tag = (
    <span
      data-gallery-tag
      className="pointer-events-none fixed bottom-1 left-1 z-50 rounded-[4px] bg-warning-bg px-1.5 py-0.5 text-[10px] leading-[14px] font-bold tracking-[.06em] text-warning"
    >
      EXEMPLO
    </span>
  );

  if (screen.kind === "login") {
    return (
      <>
        <LoginScreen>
          <LoginForm key={name} preview={screen.preview} />
        </LoginScreen>
        {tag}
      </>
    );
  }

  if (screen.kind === "widget-signin") {
    return (
      <>
        <StoreShell chat={<SignInPrompt />}>
          <StoreSections />
        </StoreShell>
        {tag}
      </>
    );
  }

  const status = screen.status ?? "ready";
  const busy = status === "submitted" || status === "streaming";
  const view = (
    <ChatView
        key={name}
        messages={screen.messages}
        status={status}
        typing={screen.typing ?? false}
        banner={screen.banner}
        answerFooter={screen.footer}
        inputDisabled={Boolean(screen.lock)}
        inputLock={screen.lock}
        busy={busy}
        onSend={() => false}
        onStop={noop}
        {...(inWidget ? { embedded: true, header: null } : {})}
      />
  );
  return (
    <>
      {inWidget ? (
        <StoreShell chat={view}>
          <StoreSections />
        </StoreShell>
      ) : (
        view
      )}
      {tag}
    </>
  );
}
