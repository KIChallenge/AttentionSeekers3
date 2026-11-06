"use client";

import { ChartLineData01Icon, Table01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { motion } from "motion/react";
import { type ReactNode, useState } from "react";
import { fmt, fmtSigned } from "@/lib/format";
import type { Evidence } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { AnimatedNumber } from "./animated-number";
import { SqlBlock } from "./code-block";
import { EvidenceChips, type EvidenceRequest, useEvidence } from "./evidence-panel";
import { type ChartSpec, StatChart } from "./stat-chart";

export type Kpi = { label: string; value: number | null; unit?: string | null; delta?: number | null; digits?: number };
export type TableSpec = { columns: (string | { key: string; label: string })[]; rows: Record<string, unknown>[] };

function colKey(c: string | { key: string; label: string }) {
  return typeof c === "string" ? c : c.key;
}
function colLabel(c: string | { key: string; label: string }) {
  return typeof c === "string" ? c : c.label;
}

/** One statistic with its definition, KPI(s), chart, table toggle, SQL and evidence chips. */
export function StatCard({
  title,
  definition,
  kpis,
  chart,
  table,
  sql,
  evidence,
  examples,
  warnings,
  header,
  actions,
  footnote,
  className,
  chartHeight,
  showSql = false,
  extraSql,
}: {
  title: string;
  definition?: string | null;
  kpis?: Kpi[];
  chart?: ChartSpec | null;
  table?: TableSpec | null;
  sql?: string | null;
  evidence?: Evidence | null;
  examples?: EvidenceRequest["examples"];
  warnings?: string[];
  header?: ReactNode;
  actions?: ReactNode;
  footnote?: ReactNode;
  className?: string;
  chartHeight?: number;
  showSql?: boolean;
  extraSql?: { title: string; sql: string }[];
}) {
  const [view, setView] = useState<"chart" | "table">(chart ? "chart" : "table");
  const openEvidence = useEvidence();
  const req: EvidenceRequest = { title, definition: definition ?? undefined, evidence, sql, examples, warnings, extraSql };
  return (
    <motion.div layout initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }} className={cn("min-w-0", className)}>
      <Card className="h-full min-w-0 gap-4 rounded-2xl border border-border bg-card p-4 shadow-none ring-0">
        <CardHeader className="gap-1 p-0">
          {header}
          <CardTitle className="text-sm font-semibold">{title}</CardTitle>
          {definition && <CardDescription className="text-xs">{definition}</CardDescription>}
          {(chart || actions) && (
            <CardAction className="flex items-center gap-1">
              {actions}
              {chart && table && (
                <ToggleGroup type="single" value={view} onValueChange={(v) => v && setView(v as "chart" | "table")} size="sm" variant="outline" aria-label="Darstellung">
                  <ToggleGroupItem value="chart" aria-label="Diagramm" className="size-7 p-0">
                    <HugeiconsIcon icon={ChartLineData01Icon} strokeWidth={2} className="size-3.5" />
                  </ToggleGroupItem>
                  <ToggleGroupItem value="table" aria-label="Tabelle" className="size-7 p-0">
                    <HugeiconsIcon icon={Table01Icon} strokeWidth={2} className="size-3.5" />
                  </ToggleGroupItem>
                </ToggleGroup>
              )}
            </CardAction>
          )}
        </CardHeader>
        <CardContent className="flex min-w-0 flex-col gap-4 p-0">
          {kpis && kpis.length > 0 && (
            <div className="flex flex-wrap gap-x-8 gap-y-3">
              {kpis.map((k) => (
                <button
                  type="button"
                  key={k.label}
                  className="flex flex-col items-start gap-0.5 rounded-lg text-left outline-offset-2 focus-visible:outline-1"
                  onClick={() => openEvidence({ ...req, value: k.value === null ? undefined : `${fmt(k.value, k.digits)}${k.unit === "%" ? " %" : ""}` })}
                  aria-label={`${k.label}: Quellennachweis öffnen`}
                >
                  <span className="text-xs text-muted-foreground">{k.label}</span>
                  <span className="flex items-baseline gap-1.5">
                    {k.value === null ? (
                      <span className="text-3xl font-medium text-muted-foreground">–</span>
                    ) : (
                      <AnimatedNumber value={k.value} digits={k.digits} className="text-3xl font-medium tabular-nums" />
                    )}
                    {k.unit && k.unit !== "Anzahl" && <span className="text-sm text-muted-foreground">{k.unit}</span>}
                    {k.delta !== undefined && k.delta !== null && (
                      <span className={cn("text-xs tabular-nums", k.delta < 0 ? "text-destructive" : "text-success")}>{fmtSigned(k.delta)}</span>
                    )}
                  </span>
                </button>
              ))}
            </div>
          )}
          {chart && view === "chart" && <StatChart spec={chart} height={chartHeight} />}
          {table && (view === "table" || !chart) && <DataTable table={table} />}
          {warnings && warnings.length > 0 && (
            <ul className="flex flex-col gap-1">
              {warnings.map((w) => (
                <li key={w} className="text-xs text-warning">
                  {w}
                </li>
              ))}
            </ul>
          )}
          {footnote && <div className="text-xs text-muted-foreground">{footnote}</div>}
          {showSql && sql && <SqlBlock code={sql} maxHeight="12rem" />}
          <EvidenceChips req={req} />
        </CardContent>
      </Card>
    </motion.div>
  );
}

export function DataTable({ table, maxHeight = "22rem" }: { table: TableSpec; maxHeight?: string }) {
  return (
    <div className="overflow-auto rounded-xl border border-border" style={{ maxHeight }}>
      <Table>
        <TableHeader className="sticky top-0 bg-card">
          <TableRow>
            {table.columns.map((c) => (
              <TableHead key={colKey(c)} className="h-8 text-xs">
                {colLabel(c)}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {table.rows.map((r, i) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: generic rows
            <TableRow key={i}>
              {table.columns.map((c) => {
                const v = r[colKey(c)];
                return (
                  <TableCell key={colKey(c)} className={cn("py-1.5 text-xs", typeof v === "number" && "text-right font-mono tabular-nums")}>
                    {typeof v === "number" ? fmt(v) : v === null || v === undefined ? "–" : String(v)}
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
