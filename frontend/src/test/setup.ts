import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
  // The chat now persists to localStorage; one test's conversation must not leak into the next.
  if (typeof localStorage !== "undefined") localStorage.clear();
});

