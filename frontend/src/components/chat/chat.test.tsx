import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Chat } from "@/components/chat/chat";
import { getMessages } from "@/lib/i18n";
import { fixtureFetch, readHttpFixture } from "@/test/fixtures";

const router = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));

const messages = getMessages();
const ANSWER = "Oi! Eu sou a Melody, da Empório da Música. 🎶 Como posso te ajudar hoje?";

function userBubbles() {
  return screen.queryAllByTestId("message-user");
}

describe("Chat", () => {
  it("shows the greeting and sends a suggestion when clicked", async () => {
    const fetch = fixtureFetch("plain-text");
    const user = userEvent.setup();
    render(<Chat fetch={fetch} />);

    expect(screen.getByText(messages.emptyState.greeting)).toBeInTheDocument();
    const suggestion = messages.emptyState.suggestions[1];
    for (const text of messages.emptyState.suggestions) {
      expect(screen.getByRole("button", { name: text })).toBeInTheDocument();
    }

    await user.click(screen.getByRole("button", { name: suggestion }));

    expect(await screen.findByText(suggestion)).toBeInTheDocument();
    expect(fetch).toHaveProperty("requests.length", 1);
    expect(screen.getByRole("textbox")).toHaveFocus();
  });

  it("keeps the typing indicator, and no empty bubble, until the first token", async () => {
    // start, start-step and text-start, then the stream holds before the first delta.
    const fetch = fixtureFetch("plain-text", { pauseAfter: 3 });
    const user = userEvent.setup();
    render(<Chat fetch={fetch} />);

    await user.type(screen.getByRole("textbox"), "Oi{Enter}");

    expect(within(userBubbles()[0]).getByText("Oi")).toBeInTheDocument();
    await waitFor(() => expect(fetch.requests).toHaveLength(1));
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.getByText(messages.status.typing)).toBeInTheDocument();
    expect(screen.queryByTestId("message-assistant")).toBeNull();

    act(() => fetch.release());
    const log = screen.getByRole("log");
    await waitFor(() => expect(log).toHaveTextContent(ANSWER));
    await waitFor(() => expect(screen.queryByText(messages.status.typing)).toBeNull());
    expect(screen.getByRole("textbox")).toBeEnabled();
  });

  it("announces the answer once it finishes, not while streaming", async () => {
    // Holds after the first delta.
    const fetch = fixtureFetch("plain-text", { pauseAfter: 4 });
    const user = userEvent.setup();
    render(<Chat fetch={fetch} />);

    await user.type(screen.getByRole("textbox"), "Oi{Enter}");
    await waitFor(() => expect(screen.getByRole("log")).toHaveTextContent("Oi! Eu sou a Melody,"));
    const live = screen.getByTestId("chat-announcer");
    expect(live).toBeEmptyDOMElement();

    act(() => fetch.release());
    await waitFor(() => expect(live).toHaveTextContent(ANSWER));
    expect(live.textContent?.trim()).toBe(ANSWER);
  });

  it("reuses the same chat id for the next message", async () => {
    const fetch = fixtureFetch("plain-text");
    const user = userEvent.setup();
    render(<Chat fetch={fetch} />);
    const textarea = screen.getByRole("textbox");

    await user.type(textarea, "Oi{Enter}");
    await waitFor(() => expect(screen.getByRole("log")).toHaveTextContent(ANSWER));
    await waitFor(() => expect(screen.getByRole("button", { name: "Enviar" })).toBeInTheDocument());
    await user.type(textarea, "Tudo bem?{Enter}");
    await waitFor(() => expect(fetch.requests).toHaveLength(2));

    expect(fetch.requests[0].id).toBeTruthy();
    expect(fetch.requests[1].id).toBe(fetch.requests[0].id);
  });

  it("sends once when Send is clicked twice in the same tick", async () => {
    const fetch = fixtureFetch("plain-text");
    const user = userEvent.setup();
    render(<Chat fetch={fetch} />);

    await user.type(screen.getByRole("textbox"), "Oi");
    const send = screen.getByRole("button", { name: "Enviar" });
    act(() => {
      fireEvent.click(send);
      fireEvent.click(send);
    });

    await waitFor(() => expect(screen.getByRole("log")).toHaveTextContent(ANSWER));
    expect(fetch.requests).toHaveLength(1);
    expect(userBubbles()).toHaveLength(1);
  });

  it("sends once on a double Enter in the same tick", async () => {
    const fetch = fixtureFetch("plain-text");
    const user = userEvent.setup();
    render(<Chat fetch={fetch} />);
    const textarea = screen.getByRole("textbox");

    await user.type(textarea, "Oi");
    act(() => {
      fireEvent.keyDown(textarea, { key: "Enter" });
      fireEvent.keyDown(textarea, { key: "Enter" });
    });

    await waitFor(() => expect(screen.getByRole("log")).toHaveTextContent(ANSWER));
    expect(fetch.requests).toHaveLength(1);
    expect(userBubbles()).toHaveLength(1);
  });

  it("keeps the partial answer on Stop without an error", async () => {
    // start, start-step, text-start and the first delta, then the stream hangs.
    const fetch = fixtureFetch("plain-text", { pauseAfter: 4 });
    const user = userEvent.setup();
    render(<Chat fetch={fetch} />);

    await user.type(screen.getByRole("textbox"), "Oi{Enter}");
    await waitFor(() => expect(screen.getByRole("log")).toHaveTextContent("Oi! Eu sou a Melody,"));
    await user.click(screen.getByRole("button", { name: "Parar" }));

    await waitFor(() => expect(screen.getByRole("textbox")).toBeEnabled());
    await waitFor(() => expect(screen.getByRole("button", { name: "Enviar" })).toBeInTheDocument());
    expect(screen.getByRole("log")).toHaveTextContent("Oi! Eu sou a Melody,");
    expect(screen.queryByRole("alert")).toBeNull();

    // The customer can send again after stopping.
    await user.type(screen.getByRole("textbox"), "Outra pergunta{Enter}");
    await waitFor(() => expect(fetch.requests).toHaveLength(2));
  });

  it("treats a finish without finishReason as a complete answer", async () => {
    const fetch = fixtureFetch("plain-text", { omitFinishReason: true });
    const user = userEvent.setup();
    render(<Chat fetch={fetch} />);

    await user.type(screen.getByRole("textbox"), "Oi{Enter}");
    await waitFor(() => expect(screen.getByTestId("chat-announcer")).toHaveTextContent(ANSWER));
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows a retryable notice when the stream ends without finishing", async () => {
    const fetch = fixtureFetch("plain-text", { truncate: true });
    const user = userEvent.setup();
    render(<Chat fetch={fetch} />);

    await user.type(screen.getByRole("textbox"), "Oi{Enter}");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(messages.errors.fallback);
    expect(within(alert).getByRole("button", { name: messages.errors.retry })).toBeInTheDocument();
    expect(screen.getByRole("log")).toHaveTextContent(ANSWER);
  });
});

describe("Chat errors and limits", () => {
  afterEach(() => {
    vi.useRealTimers();
    router.replace.mockReset();
  });

  function fakeIntervals() {
    vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] });
    return userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
  }

  it("redirects to login on 401", async () => {
    const user = userEvent.setup();
    render(<Chat fetch={fixtureFetch("http-401")} />);
    await user.type(screen.getByRole("textbox"), "Oi{Enter}");
    await waitFor(() =>
      expect(router.replace).toHaveBeenCalledWith("/login?reason=expired&callbackUrl=/"),
    );
  });

  it("locks the input during a rate limit, then retries without a second bubble", async () => {
    const user = fakeIntervals();
    const fetch = fixtureFetch(["http-429-rate-limited", "plain-text"]);
    render(<Chat fetch={fetch} />);

    await user.type(screen.getByRole("textbox"), "Oi{Enter}");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(readHttpFixture("http-429-rate-limited").body.error.message);
    expect(screen.getByRole("textbox")).toBeDisabled();

    act(() => vi.advanceTimersByTime(30_000));
    expect(screen.getByRole("textbox")).toBeEnabled();
    await user.click(screen.getByRole("button", { name: messages.errors.retry }));

    await waitFor(() => expect(screen.getByRole("log")).toHaveTextContent(ANSWER));
    expect(fetch.requests).toHaveLength(2);
    expect(userBubbles()).toHaveLength(1);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("locks the chat for the session when the budget is exhausted", async () => {
    const user = userEvent.setup();
    render(<Chat fetch={fixtureFetch("http-429-budget-exhausted")} />);
    await user.type(screen.getByRole("textbox"), "Oi{Enter}");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(readHttpFixture("http-429-budget-exhausted").body.error.message);
    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.queryByRole("button", { name: messages.errors.retry })).toBeNull();
  });

  it("retries a 500 into an answer with one user bubble and focus on the input", async () => {
    const user = userEvent.setup();
    const fetch = fixtureFetch(["http-500", "plain-text"]);
    render(<Chat fetch={fetch} />);
    await user.type(screen.getByRole("textbox"), "Oi{Enter}");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(readHttpFixture("http-500").body.error.message);
    await user.click(within(alert).getByRole("button", { name: messages.errors.retry }));

    await waitFor(() => expect(screen.getByRole("log")).toHaveTextContent(ANSWER));
    expect(userBubbles()).toHaveLength(1);
    expect(screen.getByRole("textbox")).toHaveFocus();
    const last = fetch.requests[1] as { trigger?: string };
    expect(last.trigger).toBe("regenerate-message");
  });

  it("keeps the partial answer on a stream error and offers retry", async () => {
    const user = userEvent.setup();
    render(<Chat fetch={fixtureFetch("stream-error")} />);
    await user.type(screen.getByRole("textbox"), "Oi{Enter}");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Tivemos um problema temporário para responder. Pode tentar de novo em instantes?",
    );
    expect(screen.getByRole("log")).toHaveTextContent("Deixa eu verificar isso pra você");
    expect(within(alert).getByRole("button", { name: messages.errors.retry })).toBeInTheDocument();
  });
});
