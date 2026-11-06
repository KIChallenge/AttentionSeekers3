"use client";

import { Copy01Icon, Tick02Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { highlight } from "@/lib/highlight";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function CopyButton({ text, label = "Kopieren" }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-xs"
      aria-label={label}
      title={label}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 1500);
        } catch {
          toast.error("Kopieren nicht möglich");
        }
      }}
    >
      <HugeiconsIcon icon={done ? Tick02Icon : Copy01Icon} strokeWidth={2} />
    </Button>
  );
}

/** Highlighted SQL / diff (shiki, bundled offline) with copy button. */
export function CodeBlock({
  code,
  lang = "sql",
  title,
  className,
  maxHeight = "20rem",
}: {
  code: string;
  lang?: "sql" | "diff";
  title?: string;
  className?: string;
  maxHeight?: string;
}) {
  const [html, setHtml] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    highlight(code, lang)
      .then((h) => alive && setHtml(h))
      .catch(() => alive && setHtml(null));
    return () => {
      alive = false;
    };
  }, [code, lang]);
  return (
    <div className={cn("min-w-0 overflow-hidden rounded-xl border border-border bg-muted", className)}>
      <div className="flex h-8 items-center justify-between gap-2 border-b border-border pr-1 pl-3">
        <span className="text-xs font-medium text-muted-foreground">{title ?? (lang === "sql" ? "SQL" : "Änderung (diff)")}</span>
        <CopyButton text={code} label={lang === "sql" ? "SQL kopieren" : "Diff kopieren"} />
      </div>
      <div className="overflow-auto px-3 py-2" style={{ maxHeight }}>
        {html ? (
          // biome-ignore lint/security/noDangerouslySetInnerHtml: shiki output of our own query text
          <div dangerouslySetInnerHTML={{ __html: html }} />
        ) : (
          <pre className="font-mono text-xs leading-5 whitespace-pre">{code}</pre>
        )}
      </div>
    </div>
  );
}

export const SqlBlock = (p: Omit<Parameters<typeof CodeBlock>[0], "lang">) => <CodeBlock {...p} lang="sql" />;
