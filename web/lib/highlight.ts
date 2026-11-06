"use client";

import type { HighlighterCore } from "shiki/core";

let highlighter: Promise<HighlighterCore> | null = null;

/** Offline syntax highlighter: SQL + diff grammars and GitHub light/dark themes are bundled, nothing is fetched. */
export function getHighlighter(): Promise<HighlighterCore> {
  highlighter ??= (async () => {
    const [{ createHighlighterCore }, { createJavaScriptRegexEngine }, sql, diff, light, dark] = await Promise.all([
      import("shiki/core"),
      import("shiki/engine/javascript"),
      import("shiki/langs/sql.mjs"),
      import("shiki/langs/diff.mjs"),
      import("shiki/themes/github-light.mjs"),
      import("shiki/themes/github-dark.mjs"),
    ]);
    return createHighlighterCore({
      themes: [light.default, dark.default],
      langs: [sql.default, diff.default],
      engine: createJavaScriptRegexEngine(),
    });
  })();
  return highlighter;
}

export async function highlight(code: string, lang: "sql" | "diff"): Promise<string> {
  const h = await getHighlighter();
  return h.codeToHtml(code, {
    lang,
    themes: { light: "github-light", dark: "github-dark" },
    defaultColor: false,
  });
}
