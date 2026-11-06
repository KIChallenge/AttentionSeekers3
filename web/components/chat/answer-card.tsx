"use client";

import { CheckmarkCircle02Icon, Csv01Icon, LinkSquare02Icon, Alert02Icon, Pin02Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import Link from "next/link";
import { toast } from "sonner";
import { downloadCsv } from "@/lib/csv";
import { fmt } from "@/lib/format";
import { addPin } from "@/lib/pins";
import type { Evidence, KlassExplanation } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { type ChartSpec, relativeSpread } from "@/components/stat/stat-chart";
import { DataTable, type Kpi, StatCard } from "@/components/stat/stat-card";
import { SqlBlock } from "@/components/stat/code-block";
import { TransitionGraph } from "@/components/stat/transition-graph";
import { type Quality, QualityPanel } from "./quality-panel";
import { type Sources, SourcesList } from "./sources-list";
import { Button } from "@/components/ui/button";
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card";

export type ClaimCheck = {
  passed: boolean;
  checks: number;
  numbers_checked: number;
  failed: number;
  details?: { token: string; ok: boolean; source?: string }[];
};

export type AnswerCardData = {
  title: string;
  definition?: string;
  kpis?: { label: string; value: number | null; unit?: string | null; share?: number | null; delta?: { value: number; pct?: number | null; label?: string } | number | null }[];
  chart?: (Omit<ChartSpec, "kind"> & { kind: string; stacked?: boolean }) | null;
  table?: { columns: { key: string; label: string }[]; rows: Record<string, unknown>[]; detail?: string | Record<string, unknown>[] } | null;
  sql?: string | null;
  evidence?: Evidence | null;
  warnings?: string[];
  defaults?: string[];
  notes?: string[];
  params?: Record<string, unknown>;
  claim_check?: ClaimCheck;
  kind?: string;
  explanation?: string;
  graph?: { edges: (KlassExplanation["edges"][number] & { bezeichnung_neu?: string; bezeichnung_alt?: string })[] };
  link?: string;
  unit?: string;
  quality?: Quality | null;
  readings?: Record<string, string>;
  /** files and tables the answer was computed from */
  sources?: Sources | null;
  /** the language model that picked the tool (agent mode) */
  agent?: { model: string; tool: string; arguments?: Record<string, unknown> } | null;
};

/** Backend links like /qualitaetsberichte/basis/2025-03 → this app's routes. */
function appLink(link: string) {
  const m = link.match(/^\/qualitaetsberichte\/([^/]+)\/(\d{4}-\d{2})/);
  if (m) return `/qualitaetsberichte?regelwerk=${m[1]}&monat=${m[2]}`;
  return link;
}

export function ClaimCheckBadge({ check }: { check: ClaimCheck }) {
  return (
    <HoverCard openDelay={150}>
      <HoverCardTrigger asChild>
        <button
          type="button"
          className={cn(
            "flex w-fit items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
            check.passed ? "bg-success/10 text-success" : "bg-destructive/10 text-destructive",
          )}
          aria-label="Details der Zahlenprüfung"
        >
          <HugeiconsIcon icon={check.passed ? CheckmarkCircle02Icon : Alert02Icon} strokeWidth={2} className="size-3" />
          {fmt(check.checks)} Prüfungen · {fmt(check.numbers_checked)} Zahlen geprüft
          {check.failed > 0 && ` · ${fmt(check.failed)} fehlgeschlagen`}
        </button>
      </HoverCardTrigger>
      <HoverCardContent className="w-80 text-xs">
        <p className="mb-2 font-medium">Jede Zahl im Text wurde gegen ihre Abfrage geprüft.</p>
        <ul className="flex max-h-60 flex-col gap-1 overflow-y-auto">
          {(check.details ?? []).map((d, i) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: tokens may repeat
            <li key={i} className="flex items-center gap-2">
              <span className={d.ok ? "text-success" : "text-destructive"}>{d.ok ? "✓" : "✗"}</span>
              <span className="font-mono">{d.token}</span>
              <span className="ml-auto text-muted-foreground">{d.source}</span>
            </li>
          ))}
        </ul>
      </HoverCardContent>
    </HoverCard>
  );
}

const MONTH = /^\d{4}(-\d{2})?$/; // months JJJJ-MM and years JJJJ (pensions) are a time axis
const ORDINAL = /\d/; // age groups, years … keep their order

/**
 * Best-fitting chart for an answer and ONLY the alternatives that make sense for these data (the switcher hides when one fits):
 * - time on x: line; area only for one series (stacked/overlapping areas mislead); columns only for ≤ 12 points and ≤ 3 series
 * - ordered categories (ages, age groups): columns, line for the shape of a distribution (> 5 points), bars when many
 * - unordered categories: few (≤ 8) → columns; many or long labels → bars; parts of a whole (2–6, counts) → ring
 * - several series per category (e.g. Bundesland × Geschlecht): columns or bars only
 * Long format month × category is pivoted into one line per category. The agent's wish wins when it is among the sensible kinds.
 */
function toChart(c: NonNullable<AnswerCardData["chart"]>): { spec: ChartSpec; kinds: ChartSpec["kind"][] } {
  const kind = (["line", "bar", "area", "pyramid", "hbar"].includes(c.kind) ? c.kind : "bar") as ChartSpec["kind"];
  let data = c.data;
  let series = c.series;
  let x = c.x;
  const isTime = data.length > 1 && data.every((d) => MONTH.test(String(d[x] ?? "")));
  // long format: several rows per month with a category label → one series per category
  if (isTime && series.length === 1 && new Set(data.map((d) => d[x])).size < data.length) {
    const labelKey = Object.keys(data[0] ?? {}).find((k) => k.endsWith("_label"));
    if (labelKey) {
      const v = series[0].key;
      const cats = [...new Set(data.map((d) => String(d[labelKey])))];
      const keyOf = (cat: string) => `c${cats.indexOf(cat)}`;
      const byX = new Map<string, Record<string, string | number | null>>();
      for (const d of data) {
        const row = byX.get(String(d[x])) ?? { [x]: String(d[x]) };
        row[keyOf(String(d[labelKey]))] = (d[v] as number) ?? null;
        byX.set(String(d[x]), row);
      }
      data = [...byX.values()];
      series = cats.map((cat) => ({ key: keyOf(cat), label: cat }));
    }
  }
  if (kind === "pyramid") return { spec: { kind, x, series, data, markers: c.markers, unit: c.unit }, kinds: ["pyramid", "hbar"] };
  const wanted = c.kind as ChartSpec["kind"];
  const single = series.length === 1;
  // small differences (< 30 % between smallest and largest value): bars from 0 flatten them → zoomed line / dot plot
  const spread = relativeSpread(data, series.map((s) => s.key));
  const subtle = spread < 0.3;
  if (isTime) {
    const kinds: ChartSpec["kind"][] = ["line"];
    if (single) kinds.push("area");
    if (data.length <= 12 && series.length <= 3 && !subtle) kinds.push("bar");
    const best: ChartSpec["kind"] = data.length <= 4 && series.length <= 3 && !subtle ? "bar" : "line";
    return { spec: { kind: kinds.includes(wanted) && wanted !== "bar" ? wanted : best, x, series, data, markers: c.markers, unit: c.unit, zoom: subtle },
             kinds };
  }
  // categories
  const ordinal = data.some((d) => ORDINAL.test(String(d[x] ?? "")));
  if (single && !ordinal && data.length > 4) {
    const key = series[0].key;
    data = [...data].sort((a, b) => ((b[key] as number) ?? 0) - ((a[key] as number) ?? 0));
  }
  const longLabels = data.some((d) => String(d[x] ?? "").length > 14);
  const many = data.length > 8;
  let kinds: ChartSpec["kind"][];
  let best: ChartSpec["kind"];
  if (!single) {
    kinds = many || longLabels ? ["hbar", "bar"] : ["bar", "hbar"];
    best = kinds[0];
  } else if (ordinal) {
    kinds = many ? ["bar", "hbar"] : ["bar"];
    if (data.length > 5) kinds.push("line");
    best = "bar";
  } else {
    kinds = many || longLabels ? ["hbar"] : ["bar", "hbar"];
    const parts = data.length >= 2 && data.length <= 6 && c.unit !== "%" && data.every((d) => ((d[series[0].key] as number) ?? 0) >= 0);
    if (parts) kinds.push("donut");
    best = kinds[0];
    if ((subtle || c.unit === "%") && data.length >= 2) {
      kinds.unshift("dot");                       // e.g. Fluktuationsrate je Bundesland 1,9 % … 2,3 %
      best = parts ? "donut" : subtle ? "dot" : kinds[1];             // parts of a whole (Männer/Frauen) stay a ring – shares are the message
    }
  }
  // a bar wish of the agent does not win over the dot plot when the differences are small (bars from 0 would flatten them)
  const agentWins = kinds.includes(wanted) && wanted !== "bar" && !(best === "dot" && wanted === "hbar");
  return { spec: { kind: agentWins ? wanted : best, x, series, data, markers: c.markers, unit: c.unit }, kinds };
}

const KIND_LABEL: Record<string, string> = { line: "Linie", area: "Fläche", bar: "Säulen", hbar: "Balken", donut: "Ring", pyramid: "Pyramide", dot: "Punkte" };

function graphExplanation(card: AnswerCardData): KlassExplanation | null {
  const edges = card.graph?.edges;
  if (!edges?.length) return null;
  const nodes = new Map<string, { id: string; version: string; code: string; label: string }>();
  for (const e of edges) {
    const a = `${e.version_alt}|${e.code_alt}`;
    const b = `${e.version_neu}|${e.code_neu}`;
    if (!nodes.has(a)) nodes.set(a, { id: a, version: e.version_alt, code: e.code_alt, label: e.bezeichnung_alt ?? "" });
    nodes.set(b, { id: b, version: e.version_neu, code: e.code_neu, label: e.bezeichnung_neu ?? nodes.get(b)?.label ?? "" });
  }
  return { text: card.explanation ?? "", edges, nodes: [...nodes.values()] };
}

export function AnswerCard({
  card,
  question,
  answerId,
  pinnable = true,
  onUnpin,
  onRecalc,
  recalcDisabled,
}: {
  card: AnswerCardData;
  question?: string;
  answerId?: string | number;
  pinnable?: boolean;
  onUnpin?: () => void;
  onRecalc?: (handling: Record<string, string>, freeText: Record<string, string>, summary: string) => void;
  recalcDisabled?: boolean;
}) {
  const handling = card.quality?.handling ?? null;
  const custom = !!handling && (handling.applied.some((a) => !a.default) || handling.notes.length > 0);
  const hasOfficial = !!card.table?.columns.some((c) => c.key === "offiziell");
  // table: value, official and Δ side by side (Δ only where both values came from the API)
  const table =
    card.table && hasOfficial
      ? {
          ...card.table,
          columns: [...card.table.columns.filter((c) => c.key !== "offiziell"), { key: "offiziell", label: "offiziell" }, { key: "__delta", label: "Δ" }],
          rows: card.table.rows.map((r) => ({
            ...r,
            __delta: typeof r.wert === "number" && typeof r.offiziell === "number" ? r.wert - r.offiziell : null,
          })),
        }
      : (card.table ?? null);
  const chosen = card.chart ? toChart({ ...card.chart, unit: card.chart.unit ?? card.unit }) : null; // card unit (e.g. %) for labels and the dot plot
  const [kindSel, setKindSel] = useState<ChartSpec["kind"] | null>(null);
  const chartSpec: ChartSpec | null = chosen ? { ...chosen.spec, kind: kindSel && chosen.kinds.includes(kindSel) ? kindSel : chosen.spec.kind } : null;
  if (chartSpec && custom && chartSpec.data.some((d) => "offiziell" in d) && !chartSpec.series.some((x) => x.key === "offiziell"))
    chartSpec.series = [...chartSpec.series.map((x) => ({ ...x, label: `${x.label} (eigene Behandlung)` })), { key: "offiziell", label: "offiziell", dashed: true }];
  const kpis: Kpi[] = (card.kpis ?? []).map((k) => ({
    label: k.share !== undefined && k.share !== null ? `${k.label} · ${fmt(k.share)} %` : k.label,
    value: k.value,
    unit: k.unit,
    delta: typeof k.delta === "number" ? k.delta : (k.delta?.value ?? null),
    digits: k.value !== null && !Number.isInteger(k.value) ? 1 : undefined,
  }));
  const graph = graphExplanation(card);
  const lastPeriod = (card.params?.months as string[] | undefined)?.at(-1);
  const month = lastPeriod && /^\d{4}-\d{2}$/.test(lastPeriod) ? lastPeriod : undefined; // pensions have years, no example records
  const ruleSet = (card.params?.rule_set as string | undefined) ?? "basis";
  const filters = (card.params?.filters as Record<string, string> | undefined) ?? undefined;
  const actions = (
    <>
      {chosen && chosen.kinds.length > 1 && (
        <ToggleGroup
          type="single"
          value={chartSpec?.kind}
          onValueChange={(v) => v && setKindSel(v as ChartSpec["kind"])}
          size="sm"
          variant="outline"
          aria-label="Diagrammart"
          className="mr-1"
        >
          {chosen.kinds.map((k) => (
            <ToggleGroupItem key={k} value={k} className="h-7 px-2 text-[11px]">
              {KIND_LABEL[k] ?? k}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      )}
      {card.table && card.table.rows.length > 0 && (
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Tabelle als CSV herunterladen"
          title="CSV"
          onClick={() => downloadCsv(`${card.title.replace(/[^\wäöüÄÖÜß-]+/g, "_")}.csv`, card.table!.columns, card.table!.rows)}
        >
          <HugeiconsIcon icon={Csv01Icon} strokeWidth={2} />
        </Button>
      )}
      {pinnable && (
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Ans Dashboard anheften"
          title="Ans Dashboard anheften"
          onClick={() => {
            addPin({ id: String(answerId ?? card.title), pinnedAt: new Date().toISOString(), question: question ?? card.title, card });
            toast.success("Ans Dashboard angeheftet");
          }}
        >
          <HugeiconsIcon icon={Pin02Icon} strokeWidth={2} />
        </Button>
      )}
      {onUnpin && (
        <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={onUnpin}>
          Lösen
        </Button>
      )}
    </>
  );
  return (
    <StatCard
      title={card.title}
      definition={card.definition}
      header={
        (card.claim_check || card.defaults?.length || custom) && (
          <div className="mb-1 flex flex-wrap items-center gap-1.5">
            {custom && card.warnings?.[0] && (
              <div role="note" className="mb-1 w-full rounded-xl border border-warning/40 bg-warning/10 px-3 py-2 text-xs font-medium text-warning">
                {card.warnings[0]}
              </div>
            )}
            {card.claim_check && <ClaimCheckBadge check={card.claim_check} />}
            {card.agent && (
              <span
                className="rounded-full bg-info/10 px-2 py-0.5 text-xs font-medium text-info"
                title={`Der Agent hat nur das Werkzeug und die Parameter gewählt – alle Zahlen stammen aus SQL.\n${JSON.stringify(card.agent.arguments ?? {})}`}
              >
                Agent · {card.agent.tool}
              </span>
            )}
            {card.defaults?.map((d) => (
              <span key={d} className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground" title="dokumentierte Standardannahme">
                {d}
              </span>
            ))}
          </div>
        )
      }
      kpis={kpis}
      chart={chartSpec}
      table={table}
      extraSql={handling?.sql ? [{ title: `Kopie der betroffenen Sätze (work.dq_copy, copy_id ${handling.copy_id})`, sql: handling.sql }] : undefined}
      sql={card.sql}
      evidence={card.evidence}
      warnings={custom ? card.warnings?.slice(1) : card.warnings}
      examples={month && card.kind !== "explain" && card.kind !== "quality" ? { regelwerk: ruleSet, monat: month, filter: filters } : null}
      actions={actions}
      footnote={
        (card.notes?.length || card.link || graph || card.table?.detail || card.quality?.issues.length || handling || card.sources) && (
          <div className="flex flex-col gap-3">
            {card.sources && <SourcesList sources={card.sources} />}
            {handling && (handling.applied.length > 0 || handling.notes.length > 0 || handling.hidden_months.length > 0) && (
              <div className="flex flex-col gap-2 rounded-xl border border-border p-3 text-foreground">
                <p className="text-xs font-medium">
                  Kopie der betroffenen Sätze (work.dq_copy, copy_id <span className="font-mono">{handling.copy_id}</span>)
                </p>
                <ul className="flex flex-col gap-0.5 text-xs">
                  {handling.applied.map((a) => (
                    <li key={a.problem_id}>
                      <span className="font-mono">{a.problem_id}</span> → {a.label}
                      {a.default ? " (Standard)" : ""}:{" "}
                      <span className="font-mono tabular-nums">
                        {fmt(a.removed)} entfernt / {fmt(a.added)} hinzugefügt
                      </span>
                    </li>
                  ))}
                </ul>
                {handling.hidden_months.length > 0 && <p className="text-xs text-warning">ausgeblendet: {handling.hidden_months.join(", ")} (Lücke in Grafik und Tabelle)</p>}
                {handling.notes.map((n) => (
                  <p key={n} className="text-xs text-muted-foreground">
                    {n}
                  </p>
                ))}
                {handling.sql && <SqlBlock code={handling.sql} title="Auswahl der betroffenen Sätze" maxHeight="10rem" />}
              </div>
            )}
            {card.quality && card.quality.issues.length > 0 && (
              <QualityPanel key={JSON.stringify(card.quality.issues.map((i) => i.chosen))} quality={card.quality} onRecalc={onRecalc} disabled={recalcDisabled} />
            )}
            {typeof card.table?.detail === "string" && <p>{card.table.detail}</p>}
            {Array.isArray(card.table?.detail) && card.table.detail.length > 0 && (
              <details>
                <summary className="cursor-pointer hover:text-foreground">
                  {card.params?.aggregate === "mean" ? "Monatswerte, aus denen der Durchschnitt gebildet wurde" : "Einzelwerte"} ({card.table.detail.length})
                </summary>
                <div className="mt-2">
                  <DataTable
                    table={{
                      columns: Object.keys(card.table.detail[0]).map((k) => ({ key: k, label: k === "monat" ? "Monat" : k === "wert" ? "Wert" : k })),
                      rows: card.table.detail,
                    }}
                    maxHeight="16rem"
                  />
                </div>
              </details>
            )}
            {card.notes?.map((n) => (
              <p key={n}>{n}</p>
            ))}
            {graph && (
              <>
                {card.explanation && (
                  <pre className="max-h-48 overflow-auto rounded-xl border border-border bg-muted px-3 py-2 font-sans text-xs/5 whitespace-pre-wrap text-foreground">{card.explanation}</pre>
                )}
                <TransitionGraph explanation={graph} height={300} />
              </>
            )}
            {card.link && (
              <Button asChild variant="outline" size="xs" className="w-fit">
                <Link href={appLink(card.link)}>
                  <HugeiconsIcon icon={LinkSquare02Icon} strokeWidth={2} data-icon="inline-start" />
                  Öffnen
                </Link>
              </Button>
            )}
          </div>
        )
      }
    />
  );
}
