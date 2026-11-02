import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { LoginNotice } from "@/components/login/login-notice";
import { getMessages } from "@/lib/i18n";

const params = vi.hoisted(() => ({ value: new URLSearchParams() }));
vi.mock("next/navigation", () => ({ useSearchParams: () => params.value }));

describe("LoginNotice", () => {
  it("explains an expired session", () => {
    params.value = new URLSearchParams("reason=expired&callbackUrl=/");
    render(<LoginNotice />);
    expect(screen.getByRole("status")).toHaveTextContent(getMessages().login.sessionExpired);
  });

  it("renders nothing without a reason", () => {
    params.value = new URLSearchParams();
    const { container } = render(<LoginNotice />);
    expect(container).toBeEmptyDOMElement();
  });
});
