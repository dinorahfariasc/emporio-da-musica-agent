import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ToolStatus } from "@/components/chat/tool-status";
import { getMessages } from "@/lib/i18n";

const messages = getMessages();

describe("ToolStatus", () => {
  it.each([
    ["running", "Buscando no catálogo…"],
    ["done", `Buscando no catálogo… ${messages.toolState.done}`],
    ["failed", `Buscando no catálogo… ${messages.toolState.failed}`],
  ] as const)("renders the %s state with its announced text", (state, name) => {
    render(<ToolStatus toolName="search_products" state={state} />);
    const status = screen.getByRole("status");
    expect(status).toHaveTextContent(name);
    expect(status).toHaveAttribute("data-state", state);
  });

  it("falls back for unknown tools and never shows the technical name", () => {
    const { container } = render(<ToolStatus toolName="drop_tables" state="running" />);
    expect(screen.getByText("Consultando…")).toBeInTheDocument();
    expect(container.innerHTML).not.toContain("drop_tables");
  });

  it("never shows the technical name of a known tool", () => {
    const { container } = render(<ToolStatus toolName="search_products" state="done" />);
    expect(container.innerHTML).not.toContain("search_products");
  });
});
