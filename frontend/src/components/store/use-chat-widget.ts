"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";

import {
  DESKTOP_QUERY,
  readChatWidgetState,
  setChatMaximized,
  writeChatWidgetState,
  type ChatWidgetState,
} from "@/lib/chat-widget";

function subscribeState(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-chat"] });
  return () => observer.disconnect();
}

function subscribeDesktop(onChange: () => void): () => void {
  const query = window.matchMedia(DESKTOP_QUERY);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

const isDesktop = () => window.matchMedia(DESKTOP_QUERY).matches;

// Widget controller: open state (on <html data-chat>), layout, maximised, unread dot and focus.
// Minimising and maximising only change CSS; the chat (and any running stream) stays mounted.
export function useChatWidgetController() {
  const state = useSyncExternalStore(subscribeState, readChatWidgetState, (): ChatWidgetState => "closed");
  const desktop = useSyncExternalStore(subscribeDesktop, isDesktop, () => false);
  const open = state === "open";
  const [unread, setUnread] = useState(false);
  const [maximizedChoice, setMaximizedChoice] = useState(false);
  // Desktop only: below 1024 px the open chat is already full screen.
  const maximized = open && desktop && maximizedChoice;
  const fabRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const openRef = useRef(open);
  useEffect(() => {
    openRef.current = open;
  });

  // <html data-chat-max> locks the page scroll (globals.css) while the overlay is up.
  useEffect(() => {
    setChatMaximized(maximized);
    return () => setChatMaximized(false);
  }, [maximized]);

  const toggleMaximized = useCallback(() => setMaximizedChoice((value) => !value), []);
  const restore = useCallback(() => setMaximizedChoice(false), []);

  const openChat = useCallback(() => {
    writeChatWidgetState("open", isDesktop());
    setUnread(false);
    // The attribute flips synchronously, so the panel is already displayed here.
    panelRef.current?.focus();
  }, []);

  const minimize = useCallback(() => {
    writeChatWidgetState("closed", isDesktop());
    setMaximizedChoice(false);
    fabRef.current?.focus();
  }, []);

  const markActivity = useCallback(() => {
    if (!openRef.current) setUnread(true);
  }, []);

  return {
    open,
    desktop,
    maximized,
    unread,
    openChat,
    minimize,
    toggleMaximized,
    restore,
    markActivity,
    fabRef,
    panelRef,
  };
}

export type ChatWidgetController = ReturnType<typeof useChatWidgetController>;

const OpenChatContext = createContext<() => void>(() => {});

export const OpenChatProvider = OpenChatContext.Provider;

/** Opens the chat widget from anywhere on the store page (hero call to action). */
export function useOpenChat(): () => void {
  return useContext(OpenChatContext);
}
