import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useState, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { StoreSections } from "@/components/store/store-sections";
import { StoreShell } from "@/components/store/store-shell";
import { CHAT_WIDGET_INIT_SCRIPT, CHAT_WIDGET_KEYS } from "@/lib/chat-widget";
import { getMessages } from "@/lib/i18n";

const session = vi.hoisted(() => ({ status: "unauthenticated" as string }));
const chatMounts = vi.hoisted(() => ({ count: 0 }));

vi.mock("next-auth/react", () => ({
  SessionProvider: ({ children }: { children: React.ReactNode }) => children,
  useSession: () => ({ status: session.status, data: null }),
  signOut: vi.fn(),
}));

// Stand-in for the live chat: keeps local state (to prove it stays mounted while minimised)
// and lets the test simulate a new answer from Melody.
vi.mock("@/components/chat/chat", () => ({
  Chat: ({
    onActivity,
    header,
  }: {
    onActivity?: () => void;
    header?: (onNewChat?: () => void) => ReactNode;
  }) => {
    const [count, setCount] = useState(0);
    useEffect(() => {
      chatMounts.count += 1;
    }, []);
    return (
      <div>
        {header?.(() => setCount(0))}
        <span data-testid="fake-chat-count">{count}</span>
        <button type="button" onClick={() => setCount((value) => value + 1)}>
          type
        </button>
        <button type="button" onClick={() => onActivity?.()}>
          melody answers
        </button>
      </div>
    );
  },
}));

const copy = getMessages();

function mockViewport(desktop: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockImplementation((query: string) => ({
      matches: desktop,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
}

function runInitScript() {
  new Function(CHAT_WIDGET_INIT_SCRIPT)();
}

function renderStore() {
  return render(
    <StoreShell>
      <StoreSections />
    </StoreShell>,
  );
}

const html = document.documentElement;

describe("store chat widget", () => {
  beforeEach(() => {
    session.status = "unauthenticated";
    chatMounts.count = 0;
  });

  afterEach(() => {
    cleanup(); // unmount while matchMedia is still stubbed
    delete html.dataset.chat;
    delete html.dataset.chatMax;
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("opens by default on desktop and starts minimised on mobile, so the store shows first", () => {
    mockViewport(true);
    runInitScript();
    expect(html.dataset.chat).toBe("open");

    delete html.dataset.chat;
    mockViewport(false);
    runInitScript();
    expect(html.dataset.chat).toBe("closed");
  });

  it("respects a saved choice per layout", () => {
    localStorage.setItem(CHAT_WIDGET_KEYS.mobile, "open");
    mockViewport(false);
    runInitScript();
    expect(html.dataset.chat).toBe("open");

    mockViewport(true);
    runInitScript();
    expect(html.dataset.chat).toBe("open");

    localStorage.setItem(CHAT_WIDGET_KEYS.desktop, "closed");
    runInitScript();
    expect(html.dataset.chat).toBe("closed");
  });

  it("shows Melody's intro and a sign-in link on the public page without a session", () => {
    mockViewport(true);
    runInitScript();
    renderStore();
    const link = screen.getByRole("link", { name: copy.widget.signInCta });
    expect(link).toHaveAttribute("href", "/login?callbackUrl=%2F");
    expect(screen.getByRole("heading", { level: 1, name: copy.store.hero.title })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: copy.widget.title })).toBeInTheDocument();
  });

  it("minimises to an accessible FAB, reopens, persists and returns focus", async () => {
    mockViewport(true);
    runInitScript();
    const user = userEvent.setup();
    renderStore();

    await user.click(screen.getByRole("button", { name: copy.widget.minimize }));
    expect(html.dataset.chat).toBe("closed");
    expect(localStorage.getItem(CHAT_WIDGET_KEYS.desktop)).toBe("closed");
    const fab = screen.getByRole("button", { name: copy.widget.open });
    expect(fab).toHaveFocus();
    expect(fab).toHaveAttribute("aria-expanded", "false");
    expect(fab).toHaveAttribute("aria-controls", "melody-chat");

    await user.click(fab);
    expect(html.dataset.chat).toBe("open");
    expect(localStorage.getItem(CHAT_WIDGET_KEYS.desktop)).toBe("open");
    const panel = screen.getByRole("complementary", { name: copy.widget.title });
    expect(panel).toHaveFocus();

    fireEvent.keyDown(panel, { key: "Escape" });
    expect(html.dataset.chat).toBe("closed");
    expect(fab).toHaveFocus();
  });

  it("is a modal sheet on mobile, minimised on load, with a visible way back to the store", async () => {
    mockViewport(false);
    runInitScript();
    const user = userEvent.setup();
    const { container } = renderStore();
    expect(html.dataset.chat).toBe("closed");
    expect(container.querySelector("[inert]")).toBeNull();
    await user.click(screen.getByRole("button", { name: copy.widget.open }));
    expect(screen.queryByRole("button", { name: copy.widget.maximize })).toHaveClass("max-lg:hidden");
    const dialog = screen.getByRole("dialog", { name: copy.widget.title });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(container.querySelector("[inert]")).toContainElement(
      screen.getByRole("heading", { level: 1, name: copy.store.hero.title }),
    );
    expect(localStorage.getItem(CHAT_WIDGET_KEYS.mobile)).toBe("open");
  });

  it("keeps the signed-in chat mounted while minimised and marks new answers on the FAB", async () => {
    session.status = "authenticated";
    mockViewport(true);
    runInitScript();
    const user = userEvent.setup();
    renderStore();

    await user.click(screen.getByRole("button", { name: "type" }));
    await user.click(screen.getByRole("button", { name: copy.widget.minimize }));
    expect(screen.queryByTestId("chat-fab-unread")).toBeNull();

    act(() => screen.getByRole("button", { name: "melody answers" }).click());
    expect(screen.getByTestId("chat-fab-unread")).toBeInTheDocument();
    const fab = screen.getByRole("button", { name: copy.widget.openUnread });

    await user.click(fab);
    expect(screen.queryByTestId("chat-fab-unread")).toBeNull();
    expect(screen.getByTestId("fake-chat-count")).toHaveTextContent("1");
  });

  it("shows New chat in Melody's header only when signed in", async () => {
    session.status = "authenticated";
    mockViewport(true);
    runInitScript();
    const user = userEvent.setup();
    renderStore();
    await user.click(screen.getByRole("button", { name: "type" }));
    await user.click(screen.getByRole("button", { name: copy.app.newChat }));
    expect(screen.getByTestId("fake-chat-count")).toHaveTextContent("0");
  });

  it("maximises to a modal overlay, restores with Esc, never remounts the chat and is not saved", async () => {
    session.status = "authenticated";
    mockViewport(true);
    runInitScript();
    const user = userEvent.setup();
    const { container } = renderStore();
    await user.click(screen.getByRole("button", { name: "type" }));
    expect(chatMounts.count).toBe(1);

    await user.click(screen.getByRole("button", { name: copy.widget.maximize }));
    const dialog = screen.getByRole("dialog", { name: copy.widget.title });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAttribute("data-maximized", "true");
    expect(html.dataset.chatMax).toBe("true");
    expect(container.querySelector("[inert]")).toContainElement(
      screen.getByRole("heading", { level: 1, name: copy.store.hero.title }),
    );
    expect(Object.values(CHAT_WIDGET_KEYS).map((key) => localStorage.getItem(key))).not.toContain("max");

    fireEvent.keyDown(dialog, { key: "Escape" });
    const panel = screen.getByRole("complementary", { name: copy.widget.title });
    expect(panel).not.toHaveAttribute("data-maximized");
    expect(html.dataset.chatMax).toBeUndefined();
    expect(html.dataset.chat).toBe("open");
    expect(container.querySelector("[inert]")).toBeNull();

    await user.click(screen.getByRole("button", { name: copy.widget.maximize }));
    await user.click(screen.getByRole("button", { name: copy.widget.restore }));
    expect(screen.getByRole("complementary", { name: copy.widget.title })).toBeInTheDocument();

    fireEvent.keyDown(panel, { key: "Escape" });
    expect(html.dataset.chat).toBe("closed");
    expect(screen.getByTestId("fake-chat-count")).toHaveTextContent("1");
    expect(chatMounts.count).toBe(1);
  });
});
