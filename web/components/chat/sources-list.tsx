"use client";

import { DatabaseIcon, File02Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import Link from "next/link";
import { shortHash } from "@/lib/format";
import { CopyButton } from "@/components/stat/code-block";

export type Sources = {
  files: { path: string; sha256: string; area: string; role: string; generated?: boolean }[];
  tables: string[];
};

/** Where a file can be checked again in the app. */
function fileHref(f: Sources["files"][number]): string {
  const qb = f.path.match(/qualitaetsberichte\/([^/]+)\/QB_(\d{4}-\d{2})\.md$/);
  if (qb) return `/qualitaetsberichte?regelwerk=${qb[1]}&monat=${qb[2]}`;
  const name = f.path.split("/").pop() ?? f.path;
  return `/lieferungen?ansicht=dateien&q=${encodeURIComponent(name)}`;
}

/** „Verwendete Dateien“: every file and table the answer was computed from, with SHA-256 – to check again. */
export function SourcesList({ sources }: { sources: Sources }) {
  if (!sources.files.length && !sources.tables.length) return null;
  const many = sources.files.length > 6;
  const list = (
    <ul className="flex flex-col gap-1">
      {sources.files.map((f) => (
        <li key={f.path} className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-0.5 rounded-lg border border-border px-2.5 py-1.5 text-xs">
          <HugeiconsIcon icon={File02Icon} strokeWidth={2} className="size-3.5 shrink-0 text-muted-foreground" />
          <Link href={fileHref(f)} className="min-w-0 truncate font-mono text-foreground underline decoration-dotted underline-offset-4 hover:decoration-solid" title={f.path}>
            {f.path}
          </Link>
          <span className="text-muted-foreground">{f.role}</span>
          <span className="ml-auto flex items-center gap-1 font-mono text-muted-foreground" title={`SHA-256 ${f.sha256}`}>
            {shortHash(f.sha256, 12)}
            <CopyButton text={f.sha256} label="SHA-256 kopieren" />
          </span>
        </li>
      ))}
    </ul>
  );
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border p-3 text-foreground">
      <p className="text-xs font-medium">
        Verwendete Dateien ({sources.files.length}) und Tabellen ({sources.tables.length})
      </p>
      {many ? (
        <details>
          <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">{sources.files.length} Dateien anzeigen</summary>
          <div className="mt-2">{list}</div>
        </details>
      ) : (
        list
      )}
      {sources.tables.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
          <HugeiconsIcon icon={DatabaseIcon} strokeWidth={2} className="size-3.5" />
          {sources.tables.map((t) => (
            <span key={t} className="rounded-full bg-muted px-2 py-0.5 font-mono">
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
