"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

import { getMessages, locale as defaultLocale, SUPPORTED_LOCALES, type LocaleCode } from "./index";
import type { Messages } from "./pt-BR";

const STORAGE_KEY = "melody-locale";
const listeners = new Set<() => void>();
let currentLocale: LocaleCode = defaultLocale;

function readStoredLocale(): LocaleCode {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return SUPPORTED_LOCALES.includes(stored as LocaleCode) ? (stored as LocaleCode) : defaultLocale;
  } catch {
    return defaultLocale;
  }
}

function subscribe(onStoreChange: () => void): () => void {
  listeners.add(onStoreChange);
  return () => listeners.delete(onStoreChange);
}

function getSnapshot(): LocaleCode {
  return currentLocale;
}

function getServerSnapshot(): LocaleCode {
  return defaultLocale;
}

function setLocale(next: LocaleCode): void {
  currentLocale = next;
  try {
    window.localStorage.setItem(STORAGE_KEY, next);
  } catch {
    // Storage disabled: the choice just won't persist across reloads.
  }
  for (const listener of listeners) listener();
}

type LocaleContextValue = {
  locale: LocaleCode;
  messages: Messages;
  setLocale: (locale: LocaleCode) => void;
};

// pt-BR on the server and on first paint (keeps `/` and `/login` prerendered); a stored choice
// applies right after hydration via useSyncExternalStore, so SSR and hydration still match.
export const MessagesContext = createContext<LocaleContextValue>({
  locale: defaultLocale,
  messages: getMessages(defaultLocale),
  setLocale: () => {},
});

export function LocaleProvider({ children }: { children: ReactNode }) {
  const locale = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  useEffect(() => {
    const stored = readStoredLocale();
    if (stored !== currentLocale) {
      currentLocale = stored;
      for (const listener of listeners) listener();
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const value = useMemo<LocaleContextValue>(
    () => ({ locale, messages: getMessages(locale), setLocale }),
    [locale],
  );

  return <MessagesContext.Provider value={value}>{children}</MessagesContext.Provider>;
}

export function useMessages(): Messages {
  return useContext(MessagesContext).messages;
}

export function useLocale(): { locale: LocaleCode; setLocale: (locale: LocaleCode) => void } {
  const { locale, setLocale } = useContext(MessagesContext);
  return { locale, setLocale };
}
