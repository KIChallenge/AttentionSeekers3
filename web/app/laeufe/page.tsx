"use client";

import { PlayIcon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { toast } from "sonner";
import { useApi } from "@/hooks/use-api";
import { useSseJob } from "@/hooks/use-sse-job";
import { fmt, fmtDateTime, fmtMonth, ruleSetLabel } from "@/lib/format";
import type { Delivery, Finding, Rule, Run, RunDetail, RunMetrics } from "@/lib/types";
import { Mono, StatusBadge } from "@/components/stat/badges";
import { CopyButton } from "@/components/stat/code-block";
import { PageHeading, PageShell, Panel } from "@/components/stat/page-shell";
import { ProgressCard } from "@/components/stat/progress-card";
import { FindingsList, MetricsGrid, Reconciliation, RevisionTable } from "@/components/stat/run-parts";
import { ErrorState, LoadingState } from "@/components/stat/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

type RunResult = {
  run_id: number;
  month: string;
  rule_set: string;
  rules: string[];
  checksum: string;
  metrics: RunMetrics;
  findings: Finding[] | number;
  report: { path?: string; sha256?: string } | string | null;
  published: boolean | null;
};

const KIND_NAME: Record<string, string> = {
  month: "Monatslauf",
  store: "Bestandsaufbau (store.segment)",
  classification: "Klassifikationen",
  pension: "Pensionsstatistik",
};

const RULE_SETS = [
  { id: "basis", label: "Basis – Fachbeschreibung (Stichtag)" },
  { id: "auftraege", label: "Aufträge – nach Änderungsaufträgen 1 + 2 (ganzes Monat)" },
];

export default function Page() {
  return (
    <Suspense>
      <RunsPage />
    </Suspense>
  );
}

function RunsPage() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const deliveries = useApi<{ deliveries: Delivery[] }>("/api/lieferungen");
  const rules = useApi<{ rules: Rule[] }>("/api/regeln");
  const [kind, setKind] = useState<string>("month");
  const runs = useApi<{ runs: Run[] }>(`/api/laeufe${kind === "all" ? "" : `?kind=${kind}`}`);
  const [month, setMonth] = useState<string>(params.get("monat") ?? "");
  const [ruleSet, setRuleSet] = useState("basis");
  const [preview, setPreview] = useState<string[]>([]);
  // ?lauf=ID opens the run drawer (links from Lieferungen, Quellennachweis, Qualitätsberichte)
  const laufParam = Number(params.get("lauf"));
  const detailId = Number.isFinite(laufParam) && laufParam > 0 ? laufParam : null;
  const setDetailId = (id: number | null) => {
    const p = new URLSearchParams(params.toString());
    if (id === null) p.delete("lauf");
    else p.set("lauf", String(id));
    router.replace(p.size ? `${pathname}?${p.toString()}` : pathname, { scroll: false });
  };
  const job = useSseJob<RunResult>();

  useEffect(() => {
    if (!month && deliveries.data?.deliveries.length) setMonth(deliveries.data.deliveries[deliveries.data.deliveries.length - 1].month);
  }, [deliveries.data, month]);

  const proposed = (rules.data?.rules ?? []).filter((r) => r.status === "proposed");

  async function start() {
    if (!month) return;
    const r = await job.start("/api/laeufe", { lieferung: month, regelwerk: ruleSet, vorschau: preview });
    if (r) {
      toast.success(`Lauf ${r.run_id} abgeschlossen`, { description: `${fmtMonth(r.month)} · Prüfsumme ${r.checksum}` });
      runs.reload();
    } else toast.error("Lauf fehlgeschlagen");
  }

  const res = job.result;
  return (
    <PageShell wide>
      <PageHeading
        title="Läufe"
        description="Ein Monatslauf liest eine Lieferung (und frühere) mit den freigegebenen Leseregeln, zählt nach den Zählregeln, prüft und schreibt den Qualitätsbericht. Gleiche Eingaben ergeben dieselbe Prüfsumme."
      />
      <Panel title="Monatslauf starten" description="Dauer etwa 30 Sekunden. Nur ein Auftrag gleichzeitig.">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs text-muted-foreground">Lieferung</Label>
            <Select value={month} onValueChange={setMonth}>
              <SelectTrigger className="w-56" aria-label="Lieferung">
                <SelectValue placeholder="Monat wählen" />
              </SelectTrigger>
              <SelectContent>
                {(deliveries.data?.deliveries ?? []).map((d) => (
                  <SelectItem key={d.month} value={d.month}>
                    {fmtMonth(d.month)} ({d.month})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs text-muted-foreground">Regelwerk</Label>
            <Select value={ruleSet} onValueChange={setRuleSet}>
              <SelectTrigger className="w-72" aria-label="Regelwerk">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RULE_SETS.map((r) => (
                  <SelectItem key={r.id} value={r.id}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={start} disabled={!month || job.status === "running"}>
            <HugeiconsIcon icon={PlayIcon} strokeWidth={2} data-icon="inline-start" />
            {job.status === "running" ? "Lauf läuft …" : "Lauf starten"}
          </Button>
        </div>
        {proposed.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <span className="text-xs text-muted-foreground">
              Vorschau: nicht freigegebene Regeln zusätzlich anwenden (Ergebnis ist eine Vorschau, keine Freigabe)
            </span>
            <ToggleGroup type="multiple" value={preview} onValueChange={setPreview} variant="outline" size="sm" className="flex-wrap" aria-label="Vorschau-Regeln">
              {proposed.map((r) => (
                <ToggleGroupItem key={r.rule_id} value={r.rule_id} className="px-2.5 font-mono text-xs" title={r.title}>
                  {r.rule_id}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </div>
        )}
      </Panel>

      <ProgressCard
        title={`Monatslauf ${fmtMonth(month)} · Regelwerk ${ruleSetLabel(ruleSet)}`}
        status={job.status}
        steps={job.steps.map((s) => ({ step: s.detail ?? s.step, pct: s.pct }))}
        pct={job.pct}
        error={job.error}
        elapsedMs={job.startedAt ? (job.finishedAt ?? Date.now()) - job.startedAt : undefined}
      >
        {res && (
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-medium">Lauf {res.run_id}</span>
              <span className="flex items-center gap-1 font-mono text-xs">
                Prüfsumme {res.checksum}
                <CopyButton text={res.checksum} label="Prüfsumme kopieren" />
              </span>
              {res.rules?.map((r) => (
                <Badge key={r} variant="secondary" className="font-mono">
                  {r}
                </Badge>
              ))}
              {res.published === false && <StatusBadge value="vorlaeufig" />}
              <Button variant="outline" size="xs" className="ml-auto" onClick={() => setDetailId(res.run_id)}>
                Details
              </Button>
              <Button asChild variant="outline" size="xs">
                <Link href={`/qualitaetsberichte?monat=${res.month}&regelwerk=${res.rule_set}`}>Qualitätsbericht</Link>
              </Button>
            </div>
            {res.metrics && <Reconciliation metrics={res.metrics} />}
          </div>
        )}
      </ProgressCard>

      <Panel
        title="Laufhistorie"
        action={
          <ToggleGroup type="single" value={kind} onValueChange={(v) => v && setKind(v)} variant="outline" size="sm" aria-label="Laufart">
            <ToggleGroupItem value="month" className="px-3">
              Monatsläufe
            </ToggleGroupItem>
            <ToggleGroupItem value="all" className="px-3">
              alle
            </ToggleGroupItem>
          </ToggleGroup>
        }
      >
        {runs.error ? (
          <ErrorState error={runs.error} onRetry={runs.reload} what="Läufe" />
        ) : !runs.data ? (
          <LoadingState rows={6} />
        ) : (
          <div className="max-h-[36rem] overflow-auto rounded-xl border border-border">
            <Table>
              <TableHeader className="sticky top-0 bg-card">
                <TableRow>
                  <TableHead className="text-xs">Lauf</TableHead>
                  <TableHead className="text-xs">Art</TableHead>
                  <TableHead className="text-xs">Lieferung</TableHead>
                  <TableHead className="text-xs">Regelwerk</TableHead>
                  <TableHead className="text-xs">Regeln</TableHead>
                  <TableHead className="text-right text-xs">Ergebnis</TableHead>
                  <TableHead className="text-xs">Prüfsumme</TableHead>
                  <TableHead className="text-xs">Ende</TableHead>
                  <TableHead className="text-xs">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.data.runs.map((r) => (
                  <TableRow
                    key={r.run_id}
                    className="cursor-pointer"
                    tabIndex={0}
                    onClick={() => setDetailId(r.run_id)}
                    onKeyDown={(e) => e.key === "Enter" && setDetailId(r.run_id)}
                    aria-label={`Lauf ${r.run_id} öffnen`}
                  >
                    <TableCell className="font-mono text-xs font-medium">#{r.run_id}</TableCell>
                    <TableCell className="text-xs">{r.kind_label ?? r.kind}</TableCell>
                    <TableCell className="text-xs whitespace-nowrap">{r.delivery ? fmtMonth(r.delivery) : "–"}</TableCell>
                    <TableCell className="text-xs">{r.rule_set ?? "–"}</TableCell>
                    <TableCell className="font-mono text-xs">{r.rules?.join(", ") || "–"}</TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">{fmt(r.row_count)}</TableCell>
                    <TableCell>
                      <Mono className="text-muted-foreground">{r.checksum ?? "–"}</Mono>
                    </TableCell>
                    <TableCell className="text-xs whitespace-nowrap text-muted-foreground">{fmtDateTime(r.finished_at)}</TableCell>
                    <TableCell>
                      <StatusBadge value={r.status} label={r.status_label} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Panel>
      <RunDrawer runId={detailId} onClose={() => setDetailId(null)} />
    </PageShell>
  );
}

function RunDrawer({ runId, onClose }: { runId: number | null; onClose: () => void }) {
  const detail = useApi<RunDetail>(runId === null ? null : `/api/laeufe/${runId}`);
  const d = detail.data;
  return (
    <Sheet open={runId !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-2xl">
        <SheetHeader className="gap-1 border-b border-border p-5 pr-12 text-left">
          <SheetDescription className="text-xs font-medium">Laufdetail</SheetDescription>
          <SheetTitle className="text-lg">
            Lauf {runId}
            {d?.run.delivery ? ` · ${fmtMonth(d.run.delivery)}` : d && d.run.kind !== "month" ? ` · ${KIND_NAME[d.run.kind] ?? d.run.kind}` : ""}
          </SheetTitle>
          {d && (
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <StatusBadge value={d.run.status} />
              {d.run.kind === "month" && <span>Regelwerk {ruleSetLabel(d.run.rule_set)}</span>}
              <span className="flex items-center gap-1 font-mono">
                {d.run.checksum}
                {d.run.checksum && <CopyButton text={d.run.checksum} label="Prüfsumme kopieren" />}
              </span>
              <span>{fmtDateTime(d.run.finished_at)}</span>
            </div>
          )}
        </SheetHeader>
        <div className="p-5">
          {detail.error ? (
            <ErrorState error={detail.error} what="Lauf" />
          ) : !d ? (
            <LoadingState rows={5} />
          ) : (
            <Tabs defaultValue="kennzahlen" className="gap-4">
              <TabsList className="bg-muted">
                <TabsTrigger value="kennzahlen">Kennzahlen</TabsTrigger>
                <TabsTrigger value="befunde">Befunde ({d.findings.length})</TabsTrigger>
                <TabsTrigger value="revision">Revision ({d.revisions.length})</TabsTrigger>
              </TabsList>
              <TabsContent value="kennzahlen" className="flex flex-col gap-4">
                {d.metrics && Object.keys(d.metrics).length > 0 ? (
                  <>
                    <Reconciliation metrics={d.metrics} />
                    <MetricsGrid metrics={d.metrics} />
                  </>
                ) : d.run.kind !== "month" ? (
                  // store / classification / pension runs have no monthly reconciliation – show their own summary
                  <div className="grid gap-2 sm:grid-cols-2">
                    <div className="rounded-xl border border-border p-3">
                      <div className="text-xs text-muted-foreground">Art</div>
                      <div className="text-sm font-medium">{KIND_NAME[d.run.kind] ?? d.run.kind}</div>
                    </div>
                    {d.run.row_count !== null && (
                      <div className="rounded-xl border border-border p-3">
                        <div className="text-xs text-muted-foreground">{d.run.kind === "pension" ? "Werte in stat_pensionen" : "Zeilen"}</div>
                        <div className="text-2xl font-medium tabular-nums">{fmt(d.run.row_count)}</div>
                      </div>
                    )}
                    {d.run.note && <p className="text-sm sm:col-span-2">{d.run.note}</p>}
                    {d.run.kind === "pension" && (
                      <Link href="/pensionen" className="text-xs underline underline-offset-4 sm:col-span-2">
                        Zur Pensionsstatistik
                      </Link>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">Für diesen Lauf sind keine Kennzahlen gespeichert.</p>
                )}
                {d.run.rules && d.run.rules.length > 0 && (
                  <p className="text-xs text-muted-foreground">Angewendete Regeln: {d.run.rules.join(", ")}</p>
                )}
                {d.report && (
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="font-mono">{d.report.path}</span>
                    <Mono className="text-muted-foreground" title={d.report.sha256}>
                      {d.report.sha256.slice(0, 16)}…
                    </Mono>
                    {d.run.delivery && (
                      <Button asChild variant="outline" size="xs">
                        <Link href={`/qualitaetsberichte?monat=${d.run.delivery}&regelwerk=${d.run.rule_set ?? "basis"}`}>Qualitätsbericht öffnen</Link>
                      </Button>
                    )}
                  </div>
                )}
              </TabsContent>
              <TabsContent value="befunde">
                <FindingsList findings={d.findings} month={d.run.delivery ?? ""} ruleSet={d.run.rule_set ?? "basis"} />
              </TabsContent>
              <TabsContent value="revision">
                <RevisionTable revisions={d.revisions} />
              </TabsContent>
            </Tabs>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
