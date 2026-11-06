"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";
import { Streamdown } from "streamdown";
import { useApi } from "@/hooks/use-api";
import { fmt, fmtDateTime, fmtMonth, shortHash, ruleSetLabel } from "@/lib/format";
import type { Inquiry, QbDetail, QbListItem, Rule } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Mono, StatusBadge } from "@/components/stat/badges";
import { CopyButton, SqlBlock } from "@/components/stat/code-block";
import { useEvidence } from "@/components/stat/evidence-panel";
import { PageHeading, PageShell, Panel } from "@/components/stat/page-shell";
import { FindingsList, Reconciliation, RevisionTable } from "@/components/stat/run-parts";
import { EmptyState, ErrorState, LoadingState } from "@/components/stat/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

export default function Page() {
  return (
    <Suspense fallback={<PageShell><LoadingState /></PageShell>}>
      <QualityReportsPage />
    </Suspense>
  );
}

function QualityReportsPage() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const ruleSet = params.get("regelwerk") ?? "basis";
  const month = params.get("monat");
  const view = params.get("ansicht") ?? "berichte";
  const list = useApi<{ reports: QbListItem[] }>(`/api/qualitaetsberichte?regelwerk=${ruleSet}`);

  const set = (patch: Record<string, string | null>) => {
    const p = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(patch)) v === null ? p.delete(k) : p.set(k, v);
    router.replace(`${pathname}?${p.toString()}`, { scroll: false });
  };

  useEffect(() => {
    if (!month && list.data?.reports.length) set({ monat: list.data.reports[list.data.reports.length - 1].month });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [list.data, month]);

  return (
    <PageShell wide>
      <PageHeading
        title="Qualitätsberichte"
        description="Je Berichtsmonat: Abrechnung der Sätze, alle Auffälligkeiten mit Einstufung, Beleg-Abfrage und Maßnahme, sowie der Revisionsbedarf früherer Monate. Annahmen und Rückfragen sind offen ausgewiesen."
        action={
          <ToggleGroup type="single" value={ruleSet} onValueChange={(v) => v && set({ regelwerk: v })} variant="outline" size="sm" aria-label="Regelwerk">
            <ToggleGroupItem value="basis" className="px-3">
              Basis
            </ToggleGroupItem>
            <ToggleGroupItem value="auftraege" className="px-3">
              Aufträge
            </ToggleGroupItem>
          </ToggleGroup>
        }
      />
      <Tabs value={view} onValueChange={(v) => set({ ansicht: v })} className="gap-4">
        <TabsList className="bg-muted">
          <TabsTrigger value="berichte">Berichte</TabsTrigger>
          <TabsTrigger value="annahmen">Annahmen</TabsTrigger>
          <TabsTrigger value="rueckfragen">Rückfragen</TabsTrigger>
        </TabsList>
        <TabsContent value="berichte">
          {list.error ? (
            <ErrorState error={list.error} onRetry={list.reload} what="Qualitätsberichte" />
          ) : !list.data ? (
            <LoadingState rows={8} />
          ) : list.data.reports.length === 0 ? (
            <EmptyState title="Noch keine Qualitätsberichte" description={`Für das Regelwerk „${ruleSetLabel(ruleSet)}“ wurde noch kein Monatslauf gerechnet.`} />
          ) : (
            <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
              <nav aria-label="Berichtsmonate" className="flex flex-col gap-1 lg:sticky lg:top-16 lg:max-h-[calc(100dvh-6rem)] lg:overflow-y-auto">
                {list.data.reports.map((r) => (
                  <button
                    type="button"
                    key={r.month}
                    onClick={() => set({ monat: r.month })}
                    aria-current={r.month === month ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-2 rounded-[10px] px-3 py-2 text-left text-sm transition-colors hover:bg-muted",
                      r.month === month && "bg-sidebar-accent font-medium",
                    )}
                  >
                    <span className="flex min-w-0 flex-1 flex-col">
                      <span>{fmtMonth(r.month)}</span>
                      <span className="font-mono text-xs text-muted-foreground tabular-nums">{fmt(r.total)}</span>
                    </span>
                    <span className="flex flex-col items-end gap-1">
                      <span className="text-xs text-muted-foreground tabular-nums">{fmt(r.findings)} Befunde</span>
                      {r.unexplained > 0 ? (
                        <Badge className="bg-destructive/10 text-destructive">{fmt(r.unexplained)} nicht erklärbar</Badge>
                      ) : (
                        <StatusBadge value={r.status} />
                      )}
                    </span>
                  </button>
                ))}
              </nav>
              {month ? <ReportDetail key={`${ruleSet}-${month}`} ruleSet={ruleSet} month={month} /> : null}
            </div>
          )}
        </TabsContent>
        <TabsContent value="annahmen">
          <Assumptions />
        </TabsContent>
        <TabsContent value="rueckfragen">
          <Inquiries />
        </TabsContent>
      </Tabs>
    </PageShell>
  );
}

function ReportDetail({ ruleSet, month }: { ruleSet: string; month: string }) {
  const qb = useApi<QbDetail>(`/api/qualitaetsberichte/${ruleSet}/${month}`);
  if (qb.error) return <ErrorState error={qb.error} onRetry={qb.reload} what={`Qualitätsbericht ${month}`} />;
  if (!qb.data) return <LoadingState rows={10} />;
  const d = qb.data;
  const counts = {
    explained_plausible: d.findings.filter((f) => f.classification === "explained_plausible").length,
    explained_data_problem: d.findings.filter((f) => f.classification === "explained_data_problem").length,
    unexplained: d.findings.filter((f) => f.classification === "unexplained").length,
  };
  return (
    <div className="flex min-w-0 flex-col gap-4">
      <Panel
        title={`Qualitätsbericht ${fmtMonth(month)}`}
        description={
          <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <Link href={`/laeufe?lauf=${d.run.run_id}`} className="underline decoration-dotted underline-offset-4 hover:decoration-solid">
              Lauf {d.run.run_id}
            </Link>
            <Link href={`/lieferungen?monat=${month}`} className="underline decoration-dotted underline-offset-4 hover:decoration-solid">
              Lieferung {fmtMonth(month)}
            </Link>
            <span className="font-mono">Prüfsumme {d.run.checksum}</span>
            <span>{fmtDateTime(d.report.created_at)}</span>
            <span className="flex items-center gap-1 font-mono" title={d.report.sha256}>
              {d.report.path} · {shortHash(d.report.sha256, 12)}
              <CopyButton text={d.report.sha256} label="SHA-256 des Berichts kopieren" />
            </span>
          </span>
        }
      >
        <div className="flex flex-wrap gap-2">
          <Badge className="bg-success/10 text-success">{counts.explained_plausible} erklärt – plausibel</Badge>
          <Badge className="bg-warning/10 text-warning">{counts.explained_data_problem} erklärt – Datenproblem</Badge>
          <Badge className="bg-destructive/10 text-destructive">{counts.unexplained} nicht erklärbar</Badge>
          {d.revisions.length > 0 && <Badge variant="secondary">{d.revisions.length} Monate mit Revisionsbedarf</Badge>}
        </div>
        {d.metrics && <Reconciliation metrics={d.metrics} />}
      </Panel>
      <Tabs defaultValue="befunde" className="gap-4">
        <TabsList className="bg-muted">
          <TabsTrigger value="befunde">Befunde ({d.findings.length})</TabsTrigger>
          <TabsTrigger value="revision">Revision ({d.revisions.length})</TabsTrigger>
          <TabsTrigger value="bericht">Bericht (Markdown)</TabsTrigger>
        </TabsList>
        <TabsContent value="befunde">
          <FindingsList findings={d.findings} month={month} ruleSet={ruleSet} />
        </TabsContent>
        <TabsContent value="revision" className="flex flex-col gap-2">
          <p className="text-xs text-muted-foreground">
            Veröffentlichter Wert und Wert laut aktueller Lieferung nebeneinander – nie stillschweigend ersetzt.
          </p>
          <RevisionTable revisions={d.revisions} />
        </TabsContent>
        <TabsContent value="bericht">
          <Panel>
            <div className="prose-stat min-w-0 overflow-x-auto">
              <Streamdown mode="static" controls={false}>
                {d.report.content}
              </Streamdown>
            </div>
          </Panel>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Assumptions() {
  const a = useApi<{ rules: Rule[] }>("/api/annahmen");
  if (a.error) return <ErrorState error={a.error} onRetry={a.reload} what="Annahmen" />;
  if (!a.data) return <LoadingState rows={6} />;
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      {a.data.rules.map((r) => {
        const total = (r.hits ?? []).reduce((s, h) => s + h.n, 0);
        return (
          <Panel
            key={r.rule_id}
            title={
              <span className="flex items-center gap-2">
                <Link href={`/freigaben?regel=${r.rule_id}`} className="font-mono text-xs underline decoration-dotted underline-offset-4 hover:decoration-solid">
                  {r.rule_id}
                </Link>
                <span>{r.title}</span>
              </span>
            }
            action={<StatusBadge value={r.status} label={r.status_label} />}
          >
            {r.assumption && (
              <p className="text-sm">
                <span className="font-medium">Annahme:</span> {r.assumption}
              </p>
            )}
            {r.justification && (
              <p className="text-xs text-muted-foreground">
                <span className="font-medium text-foreground">Begründung:</span> {r.justification}
              </p>
            )}
            <p className="text-xs text-muted-foreground">
              {r.approved_by ? `freigegeben von ${r.approved_by} · ${fmtDateTime(r.approved_at)}` : "noch nicht freigegeben – wird nicht angewendet"}
            </p>
            {r.hits && r.hits.length > 0 ? (
              <details>
                <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
                  Treffer in {r.hits.length} Monaten · {fmt(total)} Verhältnisse
                </summary>
                <div className="mt-2 flex flex-wrap gap-1">
                  {r.hits.map((h) => (
                    <span key={`${h.rule_set}-${h.month}`} className="rounded-full bg-muted px-2 py-0.5 font-mono text-xs tabular-nums">
                      {h.month}: {fmt(h.n)}
                    </span>
                  ))}
                </div>
              </details>
            ) : (
              <p className="text-xs text-muted-foreground">keine Treffer</p>
            )}
          </Panel>
        );
      })}
    </div>
  );
}

function Inquiries() {
  const q = useApi<{ inquiries: Inquiry[] }>("/api/rueckfragen");
  const open = useEvidence();
  if (q.error) return <ErrorState error={q.error} onRetry={q.reload} what="Rückfragen" />;
  if (!q.data) return <LoadingState rows={4} />;
  if (!q.data.inquiries.length) return <EmptyState title="Keine Rückfragen" />;
  return (
    <div className="flex flex-col gap-3">
      {q.data.inquiries.map((i) => (
        <Panel
          key={i.inquiry_id}
          title={
            <span className="flex items-center gap-2">
              <span className="font-mono text-xs">{i.inquiry_id}</span>
              <span>
                Lieferung {fmtMonth(i.delivery)} · {i.problem_id}
              </span>
            </span>
          }
          action={i.answer ? <StatusBadge value="approved" label="beantwortet" /> : <StatusBadge value="open" />}
        >
          <p className="text-sm">{i.question}</p>
          {i.proposal && <p className="text-xs text-muted-foreground">Vorschlag: {i.proposal}</p>}
          {typeof i.answer === "string" && i.answer && <p className="text-xs">Antwort: {i.answer}</p>}
          <div className="flex flex-wrap items-center gap-1.5">
            {i.extent !== null && <span className="font-mono text-xs text-muted-foreground">Umfang {fmt(i.extent)}</span>}
            {(i.example_ids ?? []).map((id) => (
              <Button
                key={id}
                variant="outline"
                size="xs"
                className="h-5 rounded-full px-2 font-mono"
                onClick={() =>
                  open({
                    title: `VVH ${id} · ${i.problem_id}`,
                    definition: i.question,
                    sql: i.evidence_sql,
                    examples: { regelwerk: "basis", monat: i.delivery, vvhIds: [id] },
                    initialTab: "saetze",
                  })
                }
              >
                VVH {id}
              </Button>
            ))}
          </div>
          {i.evidence_sql && (
            <details>
              <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">Beleg-Abfrage</summary>
              <SqlBlock code={i.evidence_sql} className="mt-2" maxHeight="10rem" />
            </details>
          )}
          <Mono className="text-muted-foreground">erstellt {fmtDateTime(i.created_at as string)}</Mono>
        </Panel>
      ))}
    </div>
  );
}
