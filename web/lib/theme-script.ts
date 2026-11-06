export const THEME_KEY = "statagent-theme";

/** Runs before hydration (app/layout.tsx), as in medlyn. */
export const THEME_SCRIPT = `try { if (localStorage.getItem("${THEME_KEY}") === "dark") document.documentElement.classList.add("dark"); } catch (e) {}`;
