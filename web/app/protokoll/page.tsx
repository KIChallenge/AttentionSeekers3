"use client";

import Link from "next/link";
import { useApi } from "@/hooks/use-api";
import { fmtDateTime } from "@/lib/format";
import type { ProtocolEntry } from "@/lib/types";
import { CopyButton } from "@/components/stat/code-block";
import { PageHeading, PageShell, Panel } from "@/components/stat/page-shell";
import { EmptyState, ErrorState, LoadingState } from "@/components/stat/states";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function ProtocolPage() {
  const p = useApi<{ entries: ProtocolEntry[]; commit_message: string }>("/api/protokoll");
  return (
    <PageShell wide>
      <PageHeading
        title="Protokoll"
        description="Jede Änderung mit Anweisung, Freigabe durch eine Person und Commit. Das Protokoll wird nur ergänzt, nie überschrieben (protokoll/protokoll.md)."
      />
      {p.error ? (
        <ErrorState error={p.error} onRetry={p.reload} what="Protokoll" />
      ) : !p.data ? (
        <LoadingState rows={6} />
      ) : (
        <>
          {p.data.commit_message && (
            <Panel
              title="Vorgeschlagene Commit-Nachricht"
              description="Das Team committet selbst – eine Änderung je Commit."
              action={<CopyButton text={p.data.commit_message} label="Commit-Nachricht kopieren" />}
            >
              <pre className="overflow-x-auto rounded-xl border border-border bg-muted p-3 font-mono text-xs whitespace-pre-wrap">{p.data.commit_message}</pre>
            </Panel>
          )}
          {p.data.entries.length === 0 ? (
            <EmptyState title="Noch keine Einträge" />
          ) : (
            <div className="overflow-x-auto rounded-xl border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Nr.</TableHead>
                    <TableHead className="text-xs">Zeitpunkt</TableHead>
                    <TableHead className="text-xs">Objekt</TableHead>
                    <TableHead className="text-xs">Änderung</TableHead>
                    <TableHead className="text-xs">Anweisung</TableHead>
                    <TableHead className="text-xs">Freigegeben von</TableHead>
                    <TableHead className="text-xs">Commit</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {p.data.entries.map((e) => (
                    <TableRow key={e.log_id}>
                      <TableCell className="font-mono text-xs">{e.log_id}</TableCell>
                      <TableCell className="text-xs whitespace-nowrap text-muted-foreground">{fmtDateTime(e.logged_at)}</TableCell>
                      <TableCell className="font-mono text-xs">
                        {objectHref(e.object) ? (
                          <Link href={objectHref(e.object)!} className="underline decoration-dotted underline-offset-4 hover:decoration-solid">
                            {e.object}
                          </Link>
                        ) : (
                          e.object
                        )}
                      </TableCell>
                      <TableCell className="min-w-72 text-xs">{e.change}</TableCell>
                      <TableCell className="min-w-48 text-xs text-muted-foreground">{e.instruction || "–"}</TableCell>
                      <TableCell className="text-xs font-medium">
                        {e.approved_by || <span className="font-normal text-muted-foreground">– (offen)</span>}
                      </TableCell>
                      <TableCell className="font-mono text-xs">{e.git_commit ? e.git_commit.slice(0, 10) : "–"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </>
      )}
    </PageShell>
  );
}

/** "rule:R-DQ01" → Freigaben, "month:basis:2024-08" → Qualitätsbericht, "run:12" → Läufe, "code:C-001" → Freigaben. */
function objectHref(object: string | null | undefined): string | null {
  if (!object) return null;
  const [kind, a, b] = object.split(":");
  if (kind === "rule" && a) return `/freigaben?regel=${a}`;
  if (kind === "month" && a && b) return `/qualitaetsberichte?regelwerk=${a}&monat=${b}`;
  if (kind === "run" && a) return `/laeufe?lauf=${a}`;
  if (kind === "code" || kind === "delivery") return kind === "code" ? "/freigaben" : "/exporte";
  return null;
}
