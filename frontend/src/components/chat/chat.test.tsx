import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { Chat } from "@/components/chat/chat";
import { getMessages } from "@/lib/i18n";
import { fixtureFetch } from "@/test/fixtures";

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
  });

  it("streams the answer after the user bubble and typing indicator", async () => {
    const fetch = fixtureFetch("plain-text");
    const user = userEvent.setup();
    render(<Chat fetch={fetch} />);

    await user.type(screen.getByRole("textbox"), "Oi{Enter}");

    expect(within(userBubbles()[0]).getByText("Oi")).toBeInTheDocument();
    expect(screen.getByText(messages.status.typing)).toBeInTheDocument();
    const log = screen.getByRole("log");
    await waitFor(() => expect(log).toHaveTextContent(ANSWER));
    await waitFor(() => expect(screen.queryByText(messages.status.typing)).toBeNull());

    const live = screen.getByTestId("chat-announcer");
    await waitFor(() => expect(live).toHaveTextContent(ANSWER));
    expect(live.textContent?.split(ANSWER)).toHaveLength(2);
    expect(screen.getByRole("textbox")).toBeEnabled();
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
