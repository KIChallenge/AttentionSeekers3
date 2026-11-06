"use client";

import Link from "next/link";
import { useState } from "react";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { fmt, fmtMonth } from "@/lib/format";
import type { Finding, Revision, RunMetrics } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ClassificationBadge } from "./badges";
import { SqlBlock } from "./code-block";
import { useEvidence } from "./evidence-panel";

const METRIC_LABELS: Record<string, string> = {
  rows_read: "gelesene Sätze",
  rows_counted: "gezählte Sätze",
  rows_not_counted: "nicht gezählt (kein Abschnitt am Stichtag)",
  rows_excluded: "ausgeschlossen / korrigiert",
  vvh_read: "gelesene Verhältnisse",
  vvh_in_period: "Verhältnisse am Stichtag",
  records_total: "Verhältnisse gesamt (Statistik)",
  records_delivery: "davon aus dieser Lieferung",
  records_carried: "davon fortgeschrieben (Annahme)",
  records_unmapped: "davon nicht zuordenbar",
  records_age_unknown: "davon Alter unbekannt",
};

/** gelesen = gezählt + nicht gezählt + ausgeschlossen – checked from the API values, never assumed. */
export function Reconciliation({ metrics }: { metrics: RunMetrics }) {
  const { rows_read: r, rows_counted: c, rows_not_counted: n, rows_excluded: x } = metrics;
  if ([r, c, n, x].some((v) => v === undefined)) return null;
  const ok = r === c + n + x;
  return (
    <div className={cn("rounded-xl border px-3 py-2 text-sm", ok ? "border-success/30 bg-success/5" : "border-destructive/30 bg-destructive/5")}>
      <div className="text-xs font-medium text-muted-foreground">Abrechnung: gelesen = gezählt + nicht gezählt + ausgeschlossen</div>
      <div className="mt-1 font-mono text-sm tabular-nums">
        {fmt(r)} = {fmt(c)} + {fmt(n)} + {fmt(x)} <span className={ok ? "text-success" : "text-destructive"}>{ok ? "✓" : "✗ Differenz " + fmt(r - c - n - x)}</span>
      </div>
    </div>
  );
}

export function MetricsGrid({ metrics }: { metrics: RunMetrics }) {
  const keys = Object.keys(metrics);
  const ordered = [...Object.keys(METRIC_LABELS).filter((k) => k in metrics), ...keys.filter((k) => !(k in METRIC_LABELS))];
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2">
      {ordered.map((k) => (
        <div key={k} className="flex items-baseline justify-between gap-3 border-b border-border py-1 text-sm">
          <dt className="text-muted-foreground">{METRIC_LABELS[k] ?? k}</dt>
          <dd className="font-mono tabular-nums">{fmt(metrics[k])}</dd>
        </div>
      ))}
    </dl>
  );
}

const LEVEL: Record<string, string> = { record: "Satz", aggregate: "Aggregat", delivery: "Lieferung" };

const FILTERS: [string, string][] = [
  ["alle", "alle"],
  ["unexplained", "nicht erklärbar"],
  ["explained_data_problem", "Datenproblem"],
  ["explained_plausible", "plausibel"],
];

export function FindingsList({ findings, month, ruleSet = "basis" }: { findings: Finding[]; month: string; ruleSet?: string }) {
  const open = useEvidence();
  const [cls, setCls] = useState("alle");
  const [level, setLevel] = useState("alle");
  if (!findings.length) return <p className="text-sm text-muted-foreground">Keine Auffälligkeiten.</p>;
  const levels = [...new Set(findings.map((f) => f.level))];
  const shown = findings.filter((f) => (cls === "alle" || f.classification === cls) && (level === "alle" || f.level === level));
  const count = (c: string) => (c === "alle" ? findings.length : findings.filter((f) => f.classification === c).length);
  return (
    <div className="flex flex-col gap-3">
      {findings.length > 6 && (
        <div className="flex flex-wrap items-center gap-2">
          <ToggleGroup type="single" value={cls} onValueChange={(v) => v && setCls(v)} variant="outline" size="sm" aria-label="Einstufung filtern">
            {FILTERS.map(([k, l]) => (
              <ToggleGroupItem key={k} value={k} className="px-2.5 text-xs" disabled={count(k) === 0}>
                {l} ({count(k)})
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          {levels.length > 1 && (
            <ToggleGroup type="single" value={level} onValueChange={(v) => v && setLevel(v)} variant="outline" size="sm" aria-label="Ebene filtern">
              <ToggleGroupItem value="alle" className="px-2.5 text-xs">alle Ebenen</ToggleGroupItem>
              {levels.map((l) => (
                <ToggleGroupItem key={l} value={l} className="px-2.5 text-xs">
                  {LEVEL[l] ?? l}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          )}
        </div>
      )}
    <ul className="flex flex-col gap-2">
      {shown.map((f, i) => (
        <li key={f.finding_id ?? i} className="flex flex-col gap-2 rounded-xl border border-border p-3">
          <div className="flex flex-wrap items-center gap-2">
            {f.problem_id && <span className="font-mono text-xs font-medium">{f.problem_id}</span>}
            <span className="text-xs text-muted-foreground">{LEVEL[f.level] ?? f.level}</span>
            {f.extent !== null && <span className="font-mono text-xs tabular-nums text-muted-foreground">Umfang {fmt(f.extent)}</span>}
            <span className="ml-auto">
              <ClassificationBadge value={f.classification} />
            </span>
          </div>
          <p className="text-sm">{f.description}</p>
          {f.measure && (
            <p className="text-xs text-muted-foreground">
              <span className="font-medium text-foreground">Maßnahme:</span> {f.measure}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-1.5">
            {f.rule_id && (
              <Button asChild variant="outline" size="xs" className="h-5 rounded-full px-2 font-mono">
                <Link href={`/freigaben?regel=${f.rule_id}`}>{f.rule_id}</Link>
              </Button>
            )}
            {f.inquiry_id && (
              <span className="rounded-full bg-info/10 px-2 py-0.5 font-mono text-xs text-info" title="Rückfrage an den Datenlieferanten">
                {f.inquiry_id}
              </span>
            )}
            {(f.example_ids ?? []).map((id) => (
              <Button
                key={id}
                variant="outline"
                size="xs"
                className="h-5 rounded-full px-2 font-mono text-xs"
                aria-label={`Sätze von VVH ${id} anzeigen`}
                onClick={() =>
                  open({
                    title: `VVH ${id} · ${f.problem_id ?? "Befund"} · ${fmtMonth(month)}`,
                    definition: f.description,
                    sql: f.evidence_sql,
                    examples: { regelwerk: ruleSet, monat: month, vvhIds: [id] },
                    initialTab: "saetze",
                  })
                }
              >
                VVH {id}
              </Button>
            ))}
            {f.evidence_sql && !f.example_ids?.length && (
              <Button
                variant="outline"
                size="xs"
                className="h-5 rounded-full px-2 text-xs"
                onClick={() => open({ title: `${f.problem_id ?? "Befund"} · ${fmtMonth(month)}`, definition: f.description, sql: f.evidence_sql, initialTab: "sql" })}
              >
                Beleg (SQL)
              </Button>
            )}
          </div>
          {f.evidence_sql && f.example_ids?.length ? (
            <details className="text-xs">
              <summary className="cursor-pointer text-muted-foreground hover:text-foreground">Beleg-Abfrage</summary>
              <SqlBlock code={f.evidence_sql} className="mt-2" maxHeight="10rem" />
            </details>
          ) : null}
        </li>
      ))}
    </ul>
    </div>
  );
}

export function RevisionTable({ revisions }: { revisions: Revision[] }) {
  if (!revisions.length) return <p className="text-sm text-muted-foreground">Kein Revisionsbedarf für frühere Monate.</p>;
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="text-xs">Monat</TableHead>
            <TableHead className="text-right text-xs">veröffentlicht</TableHead>
            <TableHead className="text-right text-xs">laut aktueller Lieferung</TableHead>
            <TableHead className="text-right text-xs">Differenz</TableHead>
            <TableHead className="text-right text-xs">neu</TableHead>
            <TableHead className="text-right text-xs">entfallen</TableHead>
            <TableHead className="text-right text-xs">davon DQ-16</TableHead>
            <TableHead className="text-xs">Hauptursache</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {revisions.map((r) => {
            const d = r.published !== null && r.current !== null ? r.current - r.published : null;
            return (
              <TableRow key={r.month}>
                <TableCell className="font-medium whitespace-nowrap">{fmtMonth(r.month)}</TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">{fmt(r.published)}</TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">{fmt(r.current)}</TableCell>
                <TableCell className={cn("text-right font-mono text-xs tabular-nums", d !== null && d !== 0 && "font-medium text-warning")}>
                  {d === null ? "–" : (d > 0 ? "+" : "") + fmt(d)}
                </TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">{fmt(r.new_vvh)}</TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">{fmt(r.vanished_vvh)}</TableCell>
                <TableCell className="text-right font-mono text-xs tabular-nums">{fmt(r.vanished_dq16)}</TableCell>
                <TableCell className="min-w-64 text-xs">{r.main_cause ?? "–"}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
