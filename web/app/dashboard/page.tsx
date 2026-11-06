"use client";

import { useEffect, useMemo, useState } from "react";
import { useApi } from "@/hooks/use-api";
import { useDqMarkers } from "@/hooks/use-markers";
import { pivot, useStat } from "@/hooks/use-stat";
import { fmtMonth, ruleSetLabel } from "@/lib/format";
import type { ModelsResponse } from "@/lib/models";
import type { StatQuery, StatResult } from "@/lib/types";
import { Switch } from "@/components/stat/switch";
import { PinnedCards } from "@/components/chat/pinned-cards";
import { PageHeading, PageShell } from "@/components/stat/page-shell";
import type { ChartSpec } from "@/components/stat/stat-chart";
import { StatCard } from "@/components/stat/stat-card";
import { AbstentionState, ErrorState, LoadingState } from "@/components/stat/states";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

const ONACE_BREAK = "2025-01";

export default function DashboardPage() {
  const [ruleSet, setRuleSet] = useState("basis");
  const months = useApi<{ months: string[] }>(`/api/statistik/monate?regelwerk=${ruleSet}`);
  const otherSet = ruleSet === "basis" ? "auftraege" : "basis";
  const otherMonths = useApi<{ months: string[] }>(`/api/statistik/monate?regelwerk=${otherSet}`);
  const [month, setMonth] = useState<string>("");
  const all = months.data?.months ?? [];
  useEffect(() => {
    if (all.length && !all.includes(month)) setMonth(all[all.length - 1]);
  }, [all, month]);
  const markers = useDqMarkers();
  const [corridorOn, setCorridorOn] = useState(false);
  const models = useApi<ModelsResponse>(corridorOn ? "/api/modelle" : null);
  const corridor = useMemo(() => {
    const m = models.data?.models.find((x) => x.kind === "corridor");
    if (!m) return null;
    return new Map(
      models.data!.predictions
        .filter((p) => p.model_id === m.model_id && p.series === "total" && p.lower !== null && p.upper !== null)
        .map((p) => [p.delivery, [p.lower as number, p.upper as number]]),
    );
  }, [models.data]);
  const chartMarkers = markers.map((m) => ({ x: m.x, label: `${m.label}${m.status === "approved" ? "" : " ?"}`, tone: m.tone }));
  const ready = all.length > 0 && !!month;
  const last2008 = all.filter((m) => m < ONACE_BREAK).pop();
  const q = (p: Omit<StatQuery, "regelwerk">): StatQuery | null => (ready ? { regelwerk: ruleSet, ...p } : null);

  const total = useStat(q({ monate: all, dimensionen: [], kennzahl: "bestand" }));
  const otherTotal = useStat(otherMonths.data?.months.length ? { regelwerk: otherSet, monate: otherMonths.data.months, dimensionen: [], kennzahl: "bestand" } : null);
  const sex = useStat(q({ monate: all, dimensionen: ["geschlecht"], kennzahl: "bestand" }));
  const region = useStat(q({ monate: [month], dimensionen: ["region"], kennzahl: "bestand" }));
  const oenace = useStat(q({ monate: [month], dimensionen: ["oenace"], kennzahl: "bestand" }));
  const oenace2008 = useStat(month >= ONACE_BREAK && last2008 ? { regelwerk: ruleSet, monate: [last2008], dimensionen: ["oenace"], kennzahl: "bestand" } : null);
  const category = useStat(q({ monate: [month], dimensionen: ["kategorie"], kennzahl: "bestand" }));
  const pyramid = useStat(q({ monate: [month], dimensionen: ["altersgruppe", "geschlecht"], kennzahl: "bestand" }));
  const fluct = useStat(q({ monate: [month], dimensionen: ["oenace"], kennzahl: "fluktuationsrate" }));

  const totalChart = useMemo<ChartSpec | null>(() => {
    if (!total.data) return null;
    const other = new Map((otherTotal.data?.rows ?? []).map((r) => [r.monat, r.wert]));
    const series = [{ key: "a", label: `Regelwerk ${ruleSetLabel(ruleSet)}` }];
    if (other.size) series.push({ key: "b", label: `Regelwerk ${otherSet}` });
    const band = corridorOn && corridor ? corridor : null;
    return {
      kind: "line",
      x: "monat",
      series,
      band: band ? { key: "korridor", label: "Erwartungskorridor (Modell)" } : undefined,
      data: total.data.rows.map((r) => ({
        monat: r.monat,
        a: r.wert,
        ...(other.size ? { b: other.get(r.monat) ?? null } : {}),
        ...(band ? { korridor: band.get(r.monat) ?? null } : {}),
      })),
      markers: chartMarkers,
    };
  }, [total.data, otherTotal.data, ruleSet, otherSet, chartMarkers, corridorOn, corridor]);

  return (
    <PageShell wide>
      <PageHeading
        title="Dashboard"
        description="Kennzahlen der Beschäftigungsstatistik. Jede Grafik zeigt Definition, Abfrage und Quellennachweis; markierte Monate haben lieferungsbezogene Datenprobleme."
        action={
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs text-muted-foreground">Regelwerk</Label>
              <ToggleGroup type="single" value={ruleSet} onValueChange={(v) => v && setRuleSet(v)} variant="outline" size="sm" aria-label="Regelwerk">
                <ToggleGroupItem value="basis" className="px-3">
                  Basis
                </ToggleGroupItem>
                <ToggleGroupItem value="auftraege" className="px-3">
                  Aufträge
                </ToggleGroupItem>
              </ToggleGroup>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label className="text-xs text-muted-foreground">Berichtsmonat</Label>
              <Select value={month} onValueChange={setMonth} disabled={!all.length}>
                <SelectTrigger size="sm" className="w-40" aria-label="Berichtsmonat">
                  <SelectValue placeholder="–" />
                </SelectTrigger>
                <SelectContent>
                  {all.map((m) => (
                    <SelectItem key={m} value={m}>
                      {fmtMonth(m)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        }
      />
      <PinnedCards />
      {months.error ? (
        <ErrorState error={months.error} what="Monate" onRetry={months.reload} />
      ) : months.data && !all.length ? (
        <AbstentionState kind="nicht vorhanden" reason={`Für das Regelwerk „${ruleSetLabel(ruleSet)}“ gibt es noch keine gerechneten Monate.`} />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <Slot state={total} className="lg:col-span-2" title="Zeitreihe">
            {(d) => (
              <StatCard
                title="Beschäftigungsverhältnisse am Stichtag"
                definition={d.definition}
                actions={<Switch checked={corridorOn} onChange={setCorridorOn} label="Erwartungskorridor (Modell)" />}
                kpis={[{ label: fmtMonth(d.rows.at(-1)?.monat), value: d.rows.at(-1)?.wert ?? null }]}
                chart={totalChart}
                table={{
                  columns: [{ key: "monat", label: "Monat" }, { key: "a", label: ruleSet }, ...(totalChart?.series.length === 2 ? [{ key: "b", label: otherSet }] : [])],
                  rows: totalChart?.data ?? [],
                }}
                sql={d.sql}
                evidence={d.evidence}
                warnings={d.warnings}
                examples={{ regelwerk: ruleSet, monat: month }}
                footnote={
                  <>
                    {markers.map((m) => `${m.x}: ${m.label} (${m.rule}, ${m.status === "approved" ? "freigegeben" : "nur vorgeschlagen"})`).join(" · ")}
                    {totalChart?.series.length === 1 && ` · Regelwerk „${ruleSetLabel(otherSet)}“: noch keine Ergebnisse.`}
                    {corridorOn && models.error && ` · Erwartungskorridor: ${models.error.message}`}
                    {corridorOn && corridor && " · Grau: Erwartungskorridor des Modells (keine amtliche Zahl; trainiert auf Werten wie geliefert, ohne Leseregeln)."}
                  </>
                }
              />
            )}
          </Slot>
          <Slot state={sex} title="Geschlecht">
            {(d) => {
              const p = pivot(d.rows, "monat", "geschlecht");
              return (
                <StatCard
                  title="Männer und Frauen"
                  definition={d.definition}
                  chart={{ kind: "line", x: "monat", series: p.series, data: p.data, markers: chartMarkers }}
                  table={{ columns: [{ key: "monat", label: "Monat" }, ...p.series], rows: p.data }}
                  sql={d.sql}
                  evidence={d.evidence}
                  warnings={d.warnings}
                />
              );
            }}
          </Slot>
          <Slot state={region} title="Bundesland">
            {(d) => (
              <StatCard
                title={`Bundesland (Arbeitsort) · ${fmtMonth(month)}`}
                definition={d.definition}
                chart={barChart(d, "region", true)}
                table={tableOf(d, "region", "Bundesland")}
                sql={d.sql}
                evidence={d.evidence}
                warnings={d.warnings}
                examples={{ regelwerk: ruleSet, monat: month }}
              />
            )}
          </Slot>
          <Slot state={oenace} title="ÖNACE" className={oenace2008.data || oenace2008.loading ? "" : "lg:col-span-2"}>
            {(d) => (
              <StatCard
                title={`Wirtschaftszweig (ÖNACE ${month >= ONACE_BREAK ? "2025" : "2008"}) · ${fmtMonth(month)}`}
                definition={d.definition}
                chart={barChart(d, "oenace", true)}
                table={tableOf(d, "oenace", "Abschnitt")}
                sql={d.sql}
                evidence={d.evidence}
                warnings={d.warnings}
                footnote="Zeitreihenbruch am 01.01.2025: ÖNACE 2008 → ÖNACE 2025. Abschnitte mit gleichem Buchstaben sind nicht vergleichbar (siehe Klassifikationen → Übergänge)."
              />
            )}
          </Slot>
          {month >= ONACE_BREAK && last2008 && (
            <Slot state={oenace2008} title="ÖNACE 2008">
              {(d) => (
                <StatCard
                  title={`Wirtschaftszweig (ÖNACE 2008) · ${fmtMonth(last2008)} – letzter Monat vor dem Bruch`}
                  definition={d.definition}
                  chart={barChart(d, "oenace", true)}
                  table={tableOf(d, "oenace", "Abschnitt")}
                  sql={d.sql}
                  evidence={d.evidence}
                  warnings={d.warnings}
                  footnote="Getrennt dargestellt – keine Umrechnung zwischen den ÖNACE-Versionen."
                />
              )}
            </Slot>
          )}
          <Slot state={category} title="Kategorien">
            {(d) => (
              <StatCard
                title={`Arbeiter / Angestellte / Beamte · ${fmtMonth(month)}`}
                definition={d.definition}
                chart={barChart(d, "kategorie")}
                table={tableOf(d, "kategorie", "Kategorie")}
                sql={d.sql}
                evidence={d.evidence}
                warnings={d.warnings}
              />
            )}
          </Slot>
          <Slot state={pyramid} title="Alterspyramide">
            {(d) => {
              const p = pivot(d.rows, "altersgruppe", "geschlecht");
              const order = p.data.sort((a, b) => String(b.altersgruppe).localeCompare(String(a.altersgruppe), "de"));
              const m = p.series.find((s) => s.key === "s_M");
              const w = p.series.find((s) => s.key === "s_W");
              const series = [m, w].filter(Boolean) as { key: string; label: string }[];
              return (
                <StatCard
                  title={`Altersaufbau · ${fmtMonth(month)}`}
                  definition={d.definition}
                  chart={{ kind: "pyramid", x: "altersgruppe", series, data: order }}
                  table={{ columns: [{ key: "altersgruppe", label: "Altersgruppe" }, ...p.series], rows: order }}
                  sql={d.sql}
                  evidence={d.evidence}
                  warnings={d.warnings}
                  footnote="Links Männer, rechts Frauen. Alter unbekannt (DQ-05/06) als eigene Gruppe."
                />
              );
            }}
          </Slot>
          <Slot state={fluct} title="Fluktuation" className="lg:col-span-2">
            {(d) => (
              <StatCard
                title={`Fluktuationsrate je Wirtschaftszweig · ${fmtMonth(month)}`}
                definition={d.definition}
                chart={{ ...barChart(d, "oenace", true), unit: "%" }}
                table={tableOf(d, "oenace", "Abschnitt")}
                sql={d.sql}
                evidence={d.evidence}
                warnings={d.warnings}
              />
            )}
          </Slot>
        </div>
      )}
    </PageShell>
  );
}

function barChart(d: StatResult, dim: string, horizontal = false): ChartSpec {
  const data = d.rows.map((r) => ({ x: horizontal ? `${r[dim]} ${String(r[`${dim}_label`] ?? "").slice(0, 22)}` : String(r[`${dim}_label`] ?? r[dim]), wert: r.wert }));
  return { kind: horizontal ? "hbar" : "bar", x: "x", series: [{ key: "wert", label: d.unit === "%" ? "Rate" : "Verhältnisse" }], data, unit: d.unit };
}

function tableOf(d: StatResult, dim: string, label: string) {
  return {
    columns: [
      { key: dim, label: "Code" },
      { key: `${dim}_label`, label },
      { key: "wert", label: d.unit === "%" ? "Wert (%)" : "Wert" },
    ],
    rows: d.rows,
  };
}

function Slot({
  state,
  title,
  className,
  children,
}: {
  state: ReturnType<typeof useStat>;
  title: string;
  className?: string;
  children: (d: StatResult) => React.ReactNode;
}) {
  return (
    <div className={className}>
      {state.error ? (
        state.error.status === 422 ? (
          <AbstentionState kind={state.error.message.startsWith("nicht vorhanden") ? "nicht vorhanden" : undefined} reason={state.error.message} />
        ) : (
          <ErrorState error={state.error} what={title} />
        )
      ) : state.data ? (
        children(state.data)
      ) : (
        <div className="rounded-2xl border border-border p-4">
          <LoadingState label={`${title} wird abgefragt …`} rows={4} />
        </div>
      )}
    </div>
  );
}
