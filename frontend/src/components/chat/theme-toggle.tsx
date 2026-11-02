"use client";

import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { useMessages } from "@/lib/i18n/context";
import { THEME_STORAGE_KEY, type Theme } from "@/lib/theme";

// The theme lives on <html data-theme>. An inline script in the root layout sets it before
// first paint (stored choice, else the system preference), so this button only reads and flips it.
function subscribe(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => observer.disconnect();
}

function currentTheme(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

// `.icon-btn` (ghost, 44 px). Sun while the theme is light, moon while it is dark. The icons swap
// in CSS (data-theme), so a prerendered page never shows the wrong one before hydration.
export function ThemeToggle() {
  const { theme } = useMessages();
  const current = useSyncExternalStore(subscribe, currentTheme, () => "light" as Theme);
  const next: Theme = current === "dark" ? "light" : "dark";

  function toggle() {
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      // Private mode or storage disabled: the choice lasts for this page only.
    }
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      className="text-primary-text no-underline"
      aria-label={current === "dark" ? theme.toLight : theme.toDark}
      onClick={toggle}
    >
      <Sun aria-hidden className="size-5 in-data-[theme=dark]:hidden" />
      <Moon aria-hidden className="hidden size-5 in-data-[theme=dark]:block" />
    </Button>
  );
}
