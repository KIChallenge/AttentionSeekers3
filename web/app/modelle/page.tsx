"use client";

import { Alert02Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useMemo, useState } from "react";
import { useApi } from "@/hooks/use-api";
import { fmt, fmtDateTime, shortHash } from "@/lib/format";
import { type DetectorMetric, type Model, type ModelsResponse, type Prediction, SERIES_LABELS } from "@/lib/models";
import { cn } from "@/lib/utils";
import { CopyButton } from "@/components/stat/code-block";
import { PageHeading, PageShell, Panel, SectionTitle } from "@/components/stat/page-shell";
import { StatChart } from "@/components/stat/stat-chart";
import { ErrorState, LoadingState } from "@/components/stat/states";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

const pct = (v: number | null | undefined, d = 1) => (v === null || v === undefined ? "–" : `${fmt(v * 100, d)} %`);

export default function ModelsPage() {
  const m = useApi<ModelsResponse>("/api/modelle");
  return (
    <PageShell wide>
      <PageHeading
        title="Modelle"
        description="Erwartungskorridor und Fehlerdetektor, trainiert auf synthetischen Lieferungen (Schema synth) und bewertet auf zwei Arten: auf synthetischen Testdaten, die beim Training bewusst zurückgehalten wurden (eigener Seed – das Modell hat sie nie gesehen, so ist die Bewertung ehrlich), und auf den 24 echten Lieferungen. Modelle markieren nur – sie ändern keine Zahl."
      />
      {m.error ? (
        <ErrorState error={m.error} onRetry={m.reload} what="Modelle" />
      ) : !m.data ? (
        <LoadingState rows={6} />
      ) : (
        <ModelsBody data={m.data} />
      )}
    </PageShell>
  );
}

function ModelsBody({ data }: { data: ModelsResponse }) {
  const detector = data.models.find((x) => x.kind === "detector");
  const corridor = data.models.find((x) => x.kind === "corridor");
  return (
    <>
      <div role="note" className="flex items-start gap-3 rounded-2xl border border-warning/40 bg-warning/10 p-4 text-sm font-medium text-warning">
        <HugeiconsIcon icon={Alert02Icon} strokeWidth={2} className="mt-0.5 size-4 shrink-0" />
        {data.banner}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {corridor && <ModelCard model={corridor} title="Erwartungskorridor" />}
        {detector && <ModelCard model={detector} title="Fehlerdetektor" />}
      </div>

      {corridor && <CorridorSection model={corridor} predictions={data.predictions.filter((p) => p.model_id === corridor.model_id)} />}
      {detector && <DetectorScorecard model={detector} />}
      {detector && <DetectorSection model={detector} predictions={data.predictions.filter((p) => p.model_id === detector.model_id)} />}

      <SectionTitle>Daten: synthetische Läufe</SectionTitle>
      <div className="overflow-x-auto rounded-xl border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs">Seed</TableHead>
              <TableHead className="text-xs">Teil</TableHead>
              <TableHead className="text-right text-xs">Maßstab</TableHead>
              <TableHead className="text-right text-xs">Monate</TableHead>
              <TableHead className="text-xs">Prüfsumme</TableHead>
              <TableHead className="text-xs">Kalibrierung</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.synthetic_runs.map((r) => (
              <TableRow key={`${r.seed}-${r.split}`}>
                <TableCell className="font-mono text-xs">{r.seed}</TableCell>
                <TableCell>
                  <Badge variant="secondary">{{ train: "Training", calibration: "Kalibrierung", test: "Test – beim Training nicht verwendet" }[r.split] ?? r.split}</Badge>
                </TableCell>
                <TableCell className="text-right font-mono text-xs">{fmt(r.scale)}</TableCell>
                <TableCell className="text-right font-mono text-xs">{fmt(r.months)}</TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground" title={r.checksum}>
                  {shortHash(r.checksum, 16)}
                </TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground" title={r.calibration_hash}>
                  {shortHash(r.calibration_hash, 16)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <SectionTitle>Grenzen</SectionTitle>
      <ul className="flex list-disc flex-col gap-1.5 pl-5 text-sm">
        {data.limits.map((l) => (
          <li key={l}>{l}</li>
        ))}
      </ul>
    </>
  );
}

function Hash({ label, value }: { label: string; value: string | number | null }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border py-1 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="flex items-center gap-1 font-mono" title={String(value ?? "")}>
        {typeof value === "string" && value.length > 20 ? shortHash(value, 16) : (value ?? "–")}
        {typeof value === "string" && value.length > 20 && <CopyButton text={value} label={`${label} kopieren`} />}
      </span>
    </div>
  );
}

function ModelCard({ model, title }: { model: Model; title: string }) {
  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          {title} <Badge className="bg-warning/10 text-warning">Modell</Badge>
        </span>
      }
      description={`Version ${model.version} · trainiert ${fmtDateTime(model.trained_at)}${model.note ? ` · ${model.note}` : ""}`}
    >
      <div className="flex flex-col">
        <Hash label="Modell-ID" value={model.model_id} />
        <Hash label="Seed" value={model.seed} />
        <Hash label="Synthetischer Lauf" value={model.synth_run} />
        <Hash label="Daten-Hash" value={model.data_hash} />
        <Hash label="Modell-Hash" value={model.model_hash} />
      </div>
      {model.kind === "corridor" && (
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-xl border border-border p-3">
            <div className="text-xs text-muted-foreground">Abdeckung synthetisch (Test)</div>
            <div className="text-2xl font-medium tabular-nums">{pct(model.metrics.synthetic_test_coverage)}</div>
            <div className="text-xs text-muted-foreground">
              nominal {pct(model.metrics.nominal_coverage, 0)} · {fmt(model.metrics.synthetic_test_points)} Punkte
            </div>
          </div>
          <div className="rounded-xl border border-border p-3">
            <div className="text-xs text-muted-foreground">Eingepflanzte Fehler gefunden (synthetisch)</div>
            {Object.entries(model.metrics.synthetic_detection ?? {}).map(([k, v]) => (
              <div key={k} className="font-mono text-sm tabular-nums">
                {k}: {fmt(v.found)} / {fmt(v.planted)}
              </div>
            ))}
          </div>
          <div className="col-span-2 rounded-xl border border-border p-3">
            <div className="text-xs text-muted-foreground">Markierungen in den realen Lieferungen</div>
            <div className="text-2xl font-medium tabular-nums">{fmt(model.metrics.real_flags?.length ?? 0)}</div>
            <div className="text-xs text-muted-foreground">Punkte außerhalb des Korridors (alle Reihen) – Hinweise, keine Korrekturen.</div>
          </div>
        </div>
      )}
      {model.kind === "detector" && <DetectorSummary model={model} />}
    </Panel>
  );
}

const PROBLEM_TITLES: Record<string, string> = {
  "DQ-01": "BEGINN und ENDE vertauscht",
  "DQ-02": "Lieferung unvollständig",
  "DQ-03": "Exakt doppelte Sätze",
  "DQ-04": "Freie Dienstverträge fehlen",
};

/** Detector features in plain German: shares as %, comparisons with the previous delivery as change. */
const FEATURES: Record<string, { label: string; kind: "share" | "ratio" }> = {
  begin_empty: { label: "ENDE gesetzt, BEGINN leer", kind: "share" },
  end_before_begin: { label: "ENDE vor BEGINN", kind: "share" },
  dup_share: { label: "exakt doppelte Sätze", kind: "share" },
  month13_share: { label: "Geburtsmonat 13", kind: "share" },
  empty_share: { label: "ÖNACE leer", kind: "share" },
  fd_share: { label: "Anteil freie Dienstverträge", kind: "share" },
  retention_prev: { label: "aktive VVH des Vormonats wieder geliefert", kind: "share" },
  rows_ratio_prev: { label: "Sätze ggü. Vormonat", kind: "ratio" },
  active_ratio_prev: { label: "aktive Verhältnisse ggü. Vormonat", kind: "ratio" },
  fd_ratio_prev: { label: "freie Dienstverträge ggü. Vormonat", kind: "ratio" },
};
const FEATURE_ORDER = Object.keys(FEATURES);

function featureValue(key: string, v: number): string {
  if (FEATURES[key]?.kind === "ratio") {
    const change = (v - 1) * 100;
    return `${change >= 0 ? "+" : "−"}${fmt(Math.abs(change), 1)} %`;
  }
  return pct(v, v > 0 && v < 0.01 ? 2 : 1);
}

/** Short summary in the model card: how many error types and how the detector did on the real deliveries. */
function DetectorSummary({ model }: { model: Model }) {
  const real = Object.values(model.metrics.real_24 ?? {});
  const found = real.reduce((a, m) => a + m.tp, 0);
  const affected = real.reduce((a, m) => a + m.tp + m.fn, 0);
  const false_ = real.reduce((a, m) => a + m.fp, 0);
  return (
    <div className="grid grid-cols-3 gap-2">
      <div className="rounded-xl border border-border p-3">
        <div className="text-xs text-muted-foreground">Fehlerarten</div>
        <div className="text-2xl font-medium tabular-nums">{real.length}</div>
      </div>
      <div className="rounded-xl border border-border p-3">
        <div className="text-xs text-muted-foreground">echte Fehler erkannt</div>
        <div className="text-2xl font-medium tabular-nums">
          {fmt(found)} / {fmt(affected)}
        </div>
      </div>
      <div className="rounded-xl border border-border p-3">
        <div className="text-xs text-muted-foreground">Fehlalarme (24 Lieferungen)</div>
        <div className="text-2xl font-medium tabular-nums">{fmt(false_)}</div>
      </div>
    </div>
  );
}

function Meter({ label, value, hint }: { label: string; value: number | null; hint: string }) {
  const v = value === null ? 0 : Math.max(0, Math.min(1, value));
  const tone = value === null ? "bg-muted" : v >= 0.9 ? "bg-success" : v >= 0.6 ? "bg-warning" : "bg-destructive";
  return (
    <div className="flex flex-col gap-1" title={hint}>
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono tabular-nums">{value === null ? "–" : pct(value, 0)}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div className={cn("h-full rounded-full", tone)} style={{ width: `${v * 100}%` }} />
      </div>
    </div>
  );
}

function MetricBlock({ title, m, unit }: { title: string; m?: DetectorMetric; unit: string }) {
  if (!m) return <div className="text-xs text-muted-foreground">{title}: keine Bewertung</div>;
  const affected = m.tp + m.fn;
  return (
    <div className="flex flex-col gap-2 rounded-xl bg-muted/40 p-3">
      <div className="text-xs font-medium">{title}</div>
      <Meter label="Präzision" value={m.precision} hint="Anteil der Markierungen, die wirklich ein Fehler waren" />
      <Meter label="Trefferquote" value={m.recall} hint="Anteil der fehlerhaften Lieferungen, die markiert wurden (Recall)" />
      <Meter label="F1" value={m.f1} hint="Mittel aus Präzision und Trefferquote" />
      <p className="text-xs text-muted-foreground">
        {fmt(m.tp)} von {fmt(affected)} {unit} erkannt · {fmt(m.fp)} Fehlalarm{m.fp === 1 ? "" : "e"} · {fmt(m.n)} {unit} geprüft
      </p>
    </div>
  );
}

/** Scorecard per error type – replaces the dense „100 % / 100 % / 1,00 (5/144)“ table. */
function DetectorScorecard({ model }: { model: Model }) {
  const problems = [...new Set([...Object.keys(model.metrics.synthetic_test ?? {}), ...Object.keys(model.metrics.real_24 ?? {})])].sort();
  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          Fehlerdetektor: Trefferbilanz je Fehlerart <Badge className="bg-warning/10 text-warning">Modell</Badge>
        </span>
      }
      description="Links die synthetischen Testlieferungen (beim Training zurückgehalten, mit bekannt eingepflanzten Fehlern), rechts die 24 echten Lieferungen (Fehler laut Problems.md). Präzision = wie oft eine Markierung stimmt, Trefferquote = wie viele Fehler gefunden wurden."
    >
      <div className="grid gap-3 md:grid-cols-2">
        {problems.map((p) => (
          <div key={p} className="flex flex-col gap-3 rounded-2xl border border-border p-4">
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-xs text-muted-foreground">{p}</span>
              <span className="text-sm font-medium">{PROBLEM_TITLES[p] ?? p}</span>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <MetricBlock title="synthetisch (Test)" m={model.metrics.synthetic_test?.[p]} unit="Lieferungen" />
              <MetricBlock title="echt (24 Lieferungen)" m={model.metrics.real_24?.[p]} unit="Lieferungen" />
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function CorridorSection({ model, predictions }: { model: Model; predictions: Prediction[] }) {
  const series = useMemo(() => [...new Set(predictions.map((p) => p.series))], [predictions]);
  const [sel, setSel] = useState(series.includes("total") ? "total" : series[0]);
  const rows = predictions.filter((p) => p.series === sel).sort((a, b) => a.delivery.localeCompare(b.delivery));
  const flagged = rows.filter((r) => r.flag);
  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          Erwartungskorridor je Reihe <Badge className="bg-warning/10 text-warning">Modell</Badge>
        </span>
      }
      description={`Band = Korridor (untere–obere Grenze, Modell ${model.model_id}); Linie = Wert wie geliefert (ohne Leseregeln). Markierte Punkte liegen außerhalb des Korridors.`}
    >
      <ToggleGroup type="single" value={sel} onValueChange={(v) => v && setSel(v)} variant="outline" size="sm" className="flex-wrap" aria-label="Reihe">
        {series.map((s) => (
          <ToggleGroupItem key={s} value={s} className="px-2.5 text-xs">
            {SERIES_LABELS[s] ?? s}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
      <StatChart
        height={300}
        spec={{
          kind: "line",
          x: "monat",
          series: [{ key: "actual", label: "wie geliefert" }],
          band: { key: "band", label: "Korridor (Modell)" },
          flagKey: "flag",
          data: rows.map((r) => ({
            monat: r.delivery,
            actual: r.actual,
            band: r.lower !== null && r.upper !== null ? [r.lower, r.upper] : null,
            flag: r.flag ? 1 : 0,
          })),
          markers: rows.some((r) => r.delivery === "2025-06") ? [{ x: "2025-06", label: "DQ-01 wie geliefert", tone: "warning" }] : [],
        }}
      />
      <p className="text-xs text-muted-foreground">
        Hinweis: Die Reihen sind „wie geliefert“ – im Juni 2025 bricht der Wert wegen vertauschter Spalten (DQ-01) ein; mit Leseregel R-DQ01 ist er
        unauffällig. Für die ersten Monate gibt es keinen Korridor (zu wenig Vorgeschichte).
      </p>
      {flagged.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">Lieferung</TableHead>
                <TableHead className="text-right text-xs">wie geliefert</TableHead>
                <TableHead className="text-right text-xs">erwartet (Modell)</TableHead>
                <TableHead className="text-right text-xs">Korridor</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {flagged.map((r) => (
                <TableRow key={r.delivery}>
                  <TableCell className="font-mono text-xs">{r.delivery}</TableCell>
                  <TableCell className="text-right font-mono text-xs font-medium text-warning tabular-nums">{fmt(r.actual)}</TableCell>
                  <TableCell className="text-right font-mono text-xs tabular-nums">{fmt(r.expected)}</TableCell>
                  <TableCell className="text-right font-mono text-xs tabular-nums">
                    {fmt(r.lower)} – {fmt(r.upper)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </Panel>
  );
}

function DetectorSection({ model, predictions }: { model: Model; predictions: Prediction[] }) {
  const problems = [...new Set(predictions.map((p) => p.series))].sort();
  const deliveries = [...new Set(predictions.map((p) => p.delivery))].sort();
  const byKey = new Map(predictions.map((p) => [`${p.delivery}|${p.series}`, p]));
  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          Fehlerdetektor: Wahrscheinlichkeit je Lieferung <Badge className="bg-warning/10 text-warning">Modell</Badge>
        </span>
      }
      description={`Modell ${model.model_id}. Farbe = vorhergesagte Wahrscheinlichkeit, Rahmen = markiert. Überfahren zeigt die Merkmale. Markierungen sind Vorschläge zur Prüfung, keine Korrektur.`}
    >
      <div className="overflow-x-auto">
        <table className="w-full border-separate border-spacing-1 text-xs">
          <thead>
            <tr>
              <th className="text-left font-medium text-muted-foreground">Lieferung</th>
              {problems.map((p) => (
                <th key={p} className="font-medium text-muted-foreground">
                  <span className="font-mono">{p}</span>
                  <span className="block text-[10px] font-normal">{PROBLEM_TITLES[p] ?? ""}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {deliveries.map((d) => (
              <tr key={d}>
                <td className="pr-2 font-mono whitespace-nowrap">{d}</td>
                {problems.map((p) => {
                  const x = byKey.get(`${d}|${p}`);
                  const prob = x?.probability ?? null;
                  return (
                    <td key={p} className="p-0">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div
                            tabIndex={0}
                            className={cn(
                              "flex h-7 min-w-16 items-center justify-center rounded-md font-mono tabular-nums outline-offset-1 focus-visible:outline-1",
                              x?.flag && "ring-2 ring-destructive",
                            )}
                            style={{
                              background: prob === null ? "var(--gray-alpha-50)" : `color-mix(in srgb, var(--destructive) ${Math.round(prob * 70)}%, var(--gray-alpha-50))`,
                              color: prob !== null && prob > 0.5 ? "var(--destructive-foreground)" : undefined,
                            }}
                            aria-label={`${d} ${p}: ${prob === null ? "keine Vorhersage" : pct(prob, 0)}${x?.flag ? ", markiert" : ""}`}
                          >
                            {prob === null ? "–" : pct(prob, 0)}
                          </div>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-sm">
                          <div className="flex w-72 flex-col gap-1.5">
                            <div className="flex items-baseline justify-between gap-3">
                              <span className="font-medium">
                                Lieferung {d} · {p}
                              </span>
                              {x?.flag && <span className="rounded-full bg-destructive px-1.5 py-0.5 text-[10px] font-medium text-white">markiert</span>}
                            </div>
                            <div className="text-[11px] opacity-80">{PROBLEM_TITLES[p] ?? p}</div>
                            <div className="flex items-baseline justify-between border-t border-background/20 pt-1.5">
                              <span>Wahrscheinlichkeit (Modell)</span>
                              <span className="font-mono font-medium tabular-nums">{prob === null ? "–" : pct(prob, 0)}</span>
                            </div>
                            {x?.features && (
                              <div className="flex flex-col gap-0.5 border-t border-background/20 pt-1.5">
                                <span className="text-[11px] opacity-80">Merkmale dieser Lieferung</span>
                                {FEATURE_ORDER.filter((k) => k in x.features!).map((k) => (
                                  <div key={k} className="flex items-baseline justify-between gap-3">
                                    <span>{FEATURES[k]?.label ?? k}</span>
                                    <span className="shrink-0 font-mono whitespace-nowrap tabular-nums">{featureValue(k, x.features![k])}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                            <div className="text-[10px] opacity-70">Hinweis zur Prüfung – das Modell korrigiert keine Daten.</div>
                          </div>
                        </TooltipContent>
                      </Tooltip>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
