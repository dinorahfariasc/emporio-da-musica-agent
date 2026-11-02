export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "melody-theme";

// Runs inline in <head> before first paint: the stored choice, else the system preference.
// Kept tiny and dependency-free; it must stay in sync with THEME_STORAGE_KEY.
export const THEME_INIT_SCRIPT = `(function(){try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");if(t!=="light"&&t!=="dark"){t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.dataset.theme=t}catch(e){}})()`;
