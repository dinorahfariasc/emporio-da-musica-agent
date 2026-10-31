import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChatInput } from "@/components/chat/chat-input";

function setup(props: Partial<Parameters<typeof ChatInput>[0]> = {}) {
  const onSend = vi.fn(() => true);
  const onStop = vi.fn();
  render(<ChatInput disabled={false} busy={false} onSend={onSend} onStop={onStop} {...props} />);
  return { onSend, onStop, user: userEvent.setup(), textarea: screen.getByRole("textbox") };
}

describe("ChatInput", () => {
  it("sends the trimmed text on Enter, clears and keeps focus", async () => {
    const { onSend, user, textarea } = setup();
    await user.type(textarea, "  Oi Melody  {Enter}");
    expect(onSend).toHaveBeenCalledWith("Oi Melody");
    expect(textarea).toHaveValue("");
    expect(textarea).toHaveFocus();
  });

  it("keeps the text when the send is not started", async () => {
    const { user, textarea } = setup({ onSend: vi.fn(() => false) });
    await user.type(textarea, "Oi{Enter}");
    expect(textarea).toHaveValue("Oi");
  });

  it("inserts a newline on Shift+Enter", async () => {
    const { onSend, user, textarea } = setup();
    await user.type(textarea, "linha 1{Shift>}{Enter}{/Shift}linha 2");
    expect(textarea).toHaveValue("linha 1\nlinha 2");
    expect(onSend).not.toHaveBeenCalled();
  });

  it("does not send blank text", async () => {
    const { onSend, user, textarea } = setup();
    await user.type(textarea, "   {Enter}");
    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });

  it("limits the message to 2000 characters", () => {
    const { textarea } = setup();
    expect(textarea).toHaveAttribute("maxLength", "2000");
  });

  it("shows Stop while busy and blocks sending", async () => {
    const { onSend, onStop, user, textarea } = setup({ busy: true });
    await user.type(textarea, "Outra{Enter}");
    expect(onSend).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Parar" }));
    expect(onStop).toHaveBeenCalledOnce();
  });

  it("disables everything when disabled", () => {
    const { textarea } = setup({ disabled: true });
    expect(textarea).toBeDisabled();
    for (const button of screen.getAllByRole("button")) expect(button).toBeDisabled();
  });
});
