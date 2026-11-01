import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChatHeader } from "@/components/chat/chat-header";
import { getMessages } from "@/lib/i18n";

const signOutMock = vi.hoisted(() => vi.fn());
vi.mock("next-auth/react", () => ({ signOut: signOutMock }));

describe("ChatHeader", () => {
  it("signs out and redirects to /login when the sign-out button is clicked", async () => {
    render(<ChatHeader />);
    await userEvent.click(screen.getByRole("button", { name: getMessages().login.signOut }));
    expect(signOutMock).toHaveBeenCalledWith({ callbackUrl: "/login" });
  });
});
