"use client";

import { FileSecurityIcon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { useApi } from "@/hooks/use-api";
import { useSseJob } from "@/hooks/use-sse-job";
import { fmt, fmtBytes, fmtDateTime, fmtMonth, shortHash, ruleSetLabel } from "@/lib/format";
import type { Delivery, PackageFile } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Mono } from "@/components/stat/badges";
import { CopyButton } from "@/components/stat/code-block";
import { useEvidence } from "@/components/stat/evidence-panel";
import { PageHeading, PageShell, Panel } from "@/components/stat/page-shell";
import { ProgressCard } from "@/components/stat/progress-card";
import { ErrorState, LoadingState } from "@/components/stat/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

type Profil = { columns: { key: string; label: string }[]; rows: (Record<string, number> & { month: string })[] };
type VerifyResult = {
  ok: boolean;
  files: { path: string; state: string; sha256: string }[];
  deliveries: { month: string; logged: number; actual: number }[];
  total_rows: number;
  expected_rows: number;
};

const BASE_COLS = new Set(["row_count", "active", "active_as_delivered"]);

export default function Page() {
  return (
    <Suspense>
      <DeliveriesPage />
    </Suspense>
  );
}

function DeliveriesPage() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const view = params.get("ansicht") ?? "lieferungen";
  const focusMonth = params.get("monat");
  const focusRef = useRef<HTMLTableRowElement | null>(null);
  const setParams = (patch: Record<string, string | null>) => {
    const p = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(patch)) {
      if (v === null || v === "") p.delete(k);
      else p.set(k, v);
    }
    router.replace(p.size ? `${pathname}?${p.toString()}` : pathname, { scroll: false });
  };
  const deliveries = useApi<{ deliveries: Delivery[] }>("/api/lieferungen");
  const profil = useApi<Profil>("/api/profil");
  const files = useApi<{ files: PackageFile[] }>("/api/dateien");
  const job = useSseJob<VerifyResult>();
  const openEvidence = useEvidence();
  const [q, setQ] = useState(params.get("q") ?? "");
  useEffect(() => {
    setQ(params.get("q") ?? "");
  }, [params]);
  useEffect(() => {
    if (focusMonth && deliveries.data && profil.data) focusRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [focusMonth, deliveries.data, profil.data]);

  const problemCols = useMemo(() => (profil.data?.columns ?? []).filter((c) => !BASE_COLS.has(c.key)), [profil.data]);
  const profileByMonth = useMemo(() => new Map((profil.data?.rows ?? []).map((r) => [r.month, r])), [profil.data]);
  const maxByCol = useMemo(() => {
    const m: Record<string, number> = {};
    for (const c of problemCols) {
      const vals = (profil.data?.rows ?? []).map((r) => Number(r[c.key] ?? 0)).sort((a, b) => a - b);
      m[c.key] = vals.length ? vals[Math.floor(vals.length / 2)] : 0;
    }
    return m;
  }, [problemCols, profil.data]);

  const filteredFiles = (files.data?.files ?? []).filter((f) => !q || f.path.toLowerCase().includes(q.toLowerCase()) || f.sha256.startsWith(q.toLowerCase()));

  async function verify() {
    const r = await job.start("/api/pruefen");
    if (r) {
      if (r.ok) toast.success("Integritätsprüfung bestanden", { description: `${r.files.length} Dateien unverändert · ${fmt(r.total_rows)} Sätze` });
      else toast.error("Integritätsprüfung mit Abweichungen");
    }
  }

  const result = job.result;
  const changed = result?.files.filter((f) => f.state !== "ok" && f.state !== "unverändert") ?? [];
  const rowDiff = result?.deliveries.filter((d) => d.logged !== d.actual) ?? [];

  return (
    <PageShell wide>
      <PageHeading
        title="Lieferungen"
        description="Die 24 Monatslieferungen und alle Paketdateien werden unverändert geladen (SHA-256). Datenfehler bleiben in den Daten und werden nur über freigegebene Leseregeln behandelt."
        action={
          <Button onClick={verify} disabled={job.status === "running"}>
            <HugeiconsIcon icon={FileSecurityIcon} strokeWidth={2} data-icon="inline-start" />
            {job.status === "running" ? "Prüfung läuft …" : "Integrität prüfen"}
          </Button>
        }
      />
      <ProgressCard
        title="Integritätsprüfung (Prüfsummen und Zeilenzahlen)"
        status={job.status}
        steps={job.steps.map((s) => ({ step: s.detail ?? s.step, pct: s.pct }))}
        pct={job.pct}
        error={job.error}
        elapsedMs={job.startedAt ? (job.finishedAt ?? Date.now()) - job.startedAt : undefined}
      >
        {result && (
          <div className="flex flex-col gap-2 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className={result.ok ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive"}>{result.ok ? "bestanden" : "Abweichungen"}</Badge>
              <span>
                {fmt(result.files.length - changed.length)} von {fmt(result.files.length)} Dateien unverändert · {fmt(result.total_rows)} Sätze geladen (erwartet{" "}
                {fmt(result.expected_rows)})
              </span>
            </div>
            {changed.length > 0 && (
              <ul className="text-xs text-destructive">
                {changed.map((f) => (
                  <li key={f.path}>
                    {f.path}: {f.state}
                  </li>
                ))}
              </ul>
            )}
            {rowDiff.length > 0 && (
              <ul className="text-xs text-destructive">
                {rowDiff.map((d) => (
                  <li key={d.month}>
                    {d.month}: protokolliert {fmt(d.logged)}, tatsächlich {fmt(d.actual)}
                  </li>
                ))}
              </ul>
            )}
            <Button
              variant="outline"
              size="xs"
              className="w-fit rounded-full"
              onClick={() =>
                openEvidence({
                  title: "Integritätsprüfung",
                  value: result.ok ? "bestanden" : "Abweichungen",
                  note: `${result.files.length} Dateien mit SHA-256 geprüft, ${result.deliveries.length} Lieferungen gezählt.`,
                  extraSql: [
                    {
                      title: "Prüfsummen (Ergebnis der Prüfung)",
                      sql: result.files.map((f) => `-- ${f.state.padEnd(10)} ${f.sha256}  ${f.path}`).join("\n"),
                    },
                  ],
                  initialTab: "sql",
                })
              }
            >
              Alle Prüfsummen anzeigen
            </Button>
          </div>
        )}
      </ProgressCard>

      <Tabs value={view} onValueChange={(v) => setParams({ ansicht: v === "lieferungen" ? null : v })} className="gap-4">
        <TabsList className="bg-muted">
          <TabsTrigger value="lieferungen">Monatslieferungen</TabsTrigger>
          <TabsTrigger value="dateien">Paketdateien</TabsTrigger>
        </TabsList>
        <TabsContent value="lieferungen">
          <Panel
            title="Problemmatrix je Lieferung"
            description="Zeilen, aktive Verhältnisse am Stichtag und Umfang jedes Datenproblems (Problems.md §2.1). Hervorgehoben: Werte deutlich über dem Median der Spalte (monatsbezogene Auffälligkeit) und Abweichungen „wie geliefert“."
          >
            {deliveries.error ? (
              <ErrorState error={deliveries.error} onRetry={deliveries.reload} what="Lieferungen" />
            ) : !deliveries.data || profil.loading ? (
              <LoadingState rows={8} />
            ) : (
              <div className="overflow-x-auto rounded-xl border border-border">
                <Table className="[&_td]:py-1.5">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="sticky left-0 z-10 bg-card text-xs">Monat</TableHead>
                      <TableHead className="text-xs">Datei · SHA-256</TableHead>
                      <TableHead className="text-right text-xs">Zeilen</TableHead>
                      <TableHead className="text-right text-xs">Aktiv</TableHead>
                      <TableHead className="text-right text-xs">wie geliefert</TableHead>
                      {problemCols.map((c) => (
                        <TableHead key={c.key} className="text-right text-xs whitespace-nowrap">
                          {c.label}
                        </TableHead>
                      ))}
                      <TableHead className="text-xs">Lauf</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {deliveries.data.deliveries.map((d) => {
                      const p = profileByMonth.get(d.month) ?? d.profile ?? {};
                      const diff = p.active !== undefined && p.active_as_delivered !== undefined && p.active !== p.active_as_delivered;
                      const run = d.runs?.basis;
                      return (
                        <TableRow key={d.month} ref={d.month === focusMonth ? focusRef : undefined} className={cn(d.month === focusMonth && "bg-primary/5")}>
                          <TableCell className="sticky left-0 z-10 bg-card font-medium whitespace-nowrap">
                            <Link
                              href={`/qualitaetsberichte?monat=${d.month}&regelwerk=basis`}
                              className="underline decoration-dotted underline-offset-4 hover:decoration-solid"
                              title={`Qualitätsbericht ${fmtMonth(d.month)} öffnen`}
                            >
                              {fmtMonth(d.month)}
                            </Link>
                          </TableCell>
                          <TableCell>
                            <span className="flex items-center gap-1 whitespace-nowrap">
                              <Link href={`/lieferungen?ansicht=dateien&q=${encodeURIComponent(d.file_name)}`} title={`${d.path}\nSHA-256 ${d.sha256}\nIm Dateiregister öffnen`}>
                                <Mono className="text-muted-foreground underline decoration-dotted underline-offset-4 hover:decoration-solid">{shortHash(d.sha256, 10)}</Mono>
                              </Link>
                              <CopyButton text={d.sha256} label={`SHA-256 von ${d.file_name} kopieren`} />
                            </span>
                          </TableCell>
                          <TableCell className="text-right font-mono text-xs tabular-nums">{fmt(d.rows)}</TableCell>
                          <TableCell className="text-right font-mono text-xs tabular-nums">
                            <button
                              type="button"
                              className="underline decoration-dotted underline-offset-4 hover:decoration-solid"
                              onClick={() =>
                                openEvidence({
                                  title: `Aktive Verhältnisse ${fmtMonth(d.month)}`,
                                  value: fmt(p.active),
                                  definition: "Verhältnisse mit einem Zeitabschnitt am Stichtag (Monatsletzter), mit freigegebenen Leseregeln.",
                                  examples: { regelwerk: "basis", monat: d.month },
                                  note: `Lieferung ${d.file_name} · SHA-256 ${d.sha256}${run ? ` · Lauf ${run.run_id} · Prüfsumme ${run.checksum}` : ""}`,
                                })
                              }
                            >
                              {fmt(p.active)}
                            </button>
                          </TableCell>
                          <TableCell className={cn("text-right font-mono text-xs tabular-nums", diff && "bg-warning/10 font-medium text-warning")}>
                            {fmt(p.active_as_delivered)}
                          </TableCell>
                          {problemCols.map((c) => {
                            const v = Number(p[c.key] ?? 0);
                            // anomaly = clearly above the column median (a month-specific problem)
                            const med = maxByCol[c.key];
                            const hot = v > 0 && (med === 0 ? v >= 5 : v >= med * 2);
                            return (
                              <TableCell
                                key={c.key}
                                className={cn(
                                  "text-right font-mono text-xs tabular-nums",
                                  v === 0 && "text-muted-foreground/60",
                                  hot && "bg-warning/10 font-medium text-warning",
                                )}
                              >
                                {p[c.key] === undefined ? "–" : fmt(v)}
                              </TableCell>
                            );
                          })}
                          <TableCell className="whitespace-nowrap">
                            {run ? (
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Link href={`/laeufe?lauf=${run.run_id}`} className="underline decoration-dotted underline-offset-4 hover:decoration-solid">
                                    <Mono>#{run.run_id}</Mono>
                                  </Link>
                                </TooltipTrigger>
                                <TooltipContent>
                                  Regelwerk {ruleSetLabel(run.rule_set)} · Prüfsumme {run.checksum} · {fmtDateTime(run.finished_at)}
                                </TooltipContent>
                              </Tooltip>
                            ) : (
                              <span className="text-xs text-muted-foreground">–</span>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </Panel>
        </TabsContent>
        <TabsContent value="dateien">
          <Panel
            title={`Paketdateien${files.data ? ` (${fmt(files.data.files.length)})` : ""}`}
            description="Register aller gelieferten Dateien mit Größe, Format und SHA-256 zum Ladezeitpunkt."
            action={<Input value={q} onChange={(e) => {
                  setQ(e.target.value);
                  setParams({ q: e.target.value });
                }} placeholder="Pfad oder SHA-256 …" className="h-8 w-56" aria-label="Dateien filtern" />}
          >
            {files.error ? (
              <ErrorState error={files.error} onRetry={files.reload} what="Dateiregister" />
            ) : !files.data ? (
              <LoadingState rows={6} />
            ) : (
              <div className="max-h-[36rem] overflow-auto rounded-xl border border-border">
                <Table>
                  <TableHeader className="sticky top-0 bg-card">
                    <TableRow>
                      <TableHead className="text-xs">Pfad</TableHead>
                      <TableHead className="text-xs">Bereich</TableHead>
                      <TableHead className="text-xs">Format</TableHead>
                      <TableHead className="text-right text-xs">Größe</TableHead>
                      <TableHead className="text-right text-xs">Einheiten</TableHead>
                      <TableHead className="text-xs">SHA-256</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredFiles.map((f) => (
                      <TableRow key={f.path}>
                        <TableCell className="font-mono text-xs">{f.path}</TableCell>
                        <TableCell className="text-xs">{f.area}</TableCell>
                        <TableCell className="text-xs">{f.format}</TableCell>
                        <TableCell className="text-right font-mono text-xs tabular-nums">{fmtBytes(f.size_bytes)}</TableCell>
                        <TableCell className="text-right font-mono text-xs tabular-nums">{fmt(f.units)}</TableCell>
                        <TableCell>
                          <span className="flex items-center gap-1">
                            <Mono className="text-muted-foreground" title={f.sha256}>
                              {shortHash(f.sha256, 16)}
                            </Mono>
                            <CopyButton text={f.sha256} label="SHA-256 kopieren" />
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </Panel>
        </TabsContent>
      </Tabs>
    </PageShell>
  );
}
