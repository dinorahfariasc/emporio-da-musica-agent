import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatError } from "@/components/chat/chat-error";
import { format, getMessages } from "@/lib/i18n";

const messages = getMessages();

describe("ChatError", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("counts down a rate limit, then calls onExpire and offers retry", async () => {
    const onExpire = vi.fn();
    const onRetry = vi.fn();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <ChatError
        error={{ kind: "rate_limited", message: "Muitas mensagens.", retryAfterSeconds: 3 }}
        onRetry={onRetry}
        onExpire={onExpire}
      />,
    );

    const banner = screen.getByRole("status");
    expect(banner).toHaveTextContent(messages.errors.rateLimitedTitle);
    expect(banner).toHaveTextContent("0:03");
    const waiting = screen.getByRole("button", {
      name: format(messages.errors.retryIn, { seconds: 3 }),
    });
    expect(waiting).toBeDisabled();

    act(() => vi.advanceTimersByTime(1000));
    expect(banner).toHaveTextContent("0:02");

    act(() => vi.advanceTimersByTime(2000));
    expect(onExpire).toHaveBeenCalledOnce();
    expect(banner).toHaveTextContent(messages.errors.rateLimitedReady);
    await user.click(screen.getByRole("button", { name: messages.errors.retry }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("shows budget exhaustion without a retry", () => {
    render(
      <ChatError
        error={{ kind: "budget_exhausted", message: "Limite diário atingido." }}
        onRetry={vi.fn()}
        onExpire={vi.fn()}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(messages.errors.budgetTitle);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("offers retry for retryable errors", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <ChatError
        error={{ kind: "retryable", message: "Algo deu errado." }}
        onRetry={onRetry}
        onExpire={vi.fn()}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Algo deu errado.");
    await user.click(screen.getByRole("button", { name: messages.errors.retry }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("uses the fallback for an empty message and never renders codes", () => {
    const { container } = render(
      <ChatError error={{ kind: "retryable", message: "" }} onRetry={vi.fn()} onExpire={vi.fn()} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(messages.errors.fallback);
    expect(container).not.toHaveTextContent(/429|500|rate_limited|retryable/);
  });
});
