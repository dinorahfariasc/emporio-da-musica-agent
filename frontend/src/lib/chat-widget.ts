// Open/minimised state of the store page chat widget. It lives on <html data-chat>, set before
// first paint by CHAT_WIDGET_INIT_SCRIPT (like the theme), so the panel and the page padding
// never jump after hydration. Desktop and mobile remember their choice separately; with no saved
// choice the chat starts open on desktop (side panel) and minimised on mobile, where the sheet
// would cover the whole store page on first visit.
// Maximised (desktop only) is on <html data-chat-max> and is never saved.
export type ChatWidgetState = "open" | "closed";

export const DESKTOP_QUERY = "(min-width: 1024px)";
export const CHAT_WIDGET_KEYS = { desktop: "melody-chat-desktop", mobile: "melody-chat-mobile" } as const;

export const CHAT_WIDGET_INIT_SCRIPT = `(function(){try{var d=matchMedia("${DESKTOP_QUERY}").matches;var s=localStorage.getItem(d?"${CHAT_WIDGET_KEYS.desktop}":"${CHAT_WIDGET_KEYS.mobile}");if(s!=="open"&&s!=="closed"){s=d?"open":"closed"}document.documentElement.dataset.chat=s}catch(e){}})()`;

export function readChatWidgetState(): ChatWidgetState {
  return document.documentElement.dataset.chat === "open" ? "open" : "closed";
}

export function setChatMaximized(maximized: boolean): void {
  if (maximized) document.documentElement.dataset.chatMax = "true";
  else delete document.documentElement.dataset.chatMax;
}

export function writeChatWidgetState(state: ChatWidgetState, desktop: boolean): void {
  document.documentElement.dataset.chat = state;
  try {
    localStorage.setItem(desktop ? CHAT_WIDGET_KEYS.desktop : CHAT_WIDGET_KEYS.mobile, state);
  } catch {
    // Storage disabled: the choice lasts for this page only.
  }
}
