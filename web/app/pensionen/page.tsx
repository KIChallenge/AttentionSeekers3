"use client";

import Link from "next/link";
import { DatabaseIcon, FileSecurityIcon, PlayCircleIcon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useApi } from "@/hooks/use-api";
import { fmt, fmtDate, shortHash } from "@/lib/format";
import type { KlassEdge, KlassExplanation } from "@/lib/types";
import { cn } from "@/lib/utils";
import { CopyButton, SqlBlock } from "@/components/stat/code-block";
import { PageHeading, PageShell, Panel, SectionTitle } from "@/components/stat/page-shell";
import { type ChartSpec, StatChart } from "@/components/stat/stat-chart";
import { ErrorState, LoadingState } from "@/components/stat/states";
import { TransitionGraph } from "@/components/stat/transition-graph";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

type PValue = {
  jahr: number;
  versicherungstraeger: string;
  pensionsart: string;
  geschlecht: string;
  variable: "Pensionen" | "VorzeitigeAlterspensionen" | string;
  wert: number | null;
  status: string;
  stand: string;
};
type KEntry = { code: string; bezeichnung: string; ebene: string; uebergeordnet: string | null; gueltig_von: string | null; gueltig_bis: string | null; attribute: Record<string, unknown> };
type Pensions = {
  values: PValue[];
  carriers: KEntry[];
  types: KEntry[];
  transitions: KlassEdge[];
  run: { run_id: number; finished_at: string; row_count: number; checksum: string; note: string; status: string } | null;
  description: { name?: string; beschreibung?: string; anmerkungen?: string; fussnoten?: string; quelle?: string };
  sql: string;
};
type Cell = {
  path: string;
  sheet: string;
  cell_ref: string;
  raw_value: string;
  value: number | null;
  jahr: number;
  tabelle: number;
  bereich_raw: string;
  art_raw: string;
  geschlecht_raw: string;
  versicherungstraeger: string | null;
  pensionsart: string | null;
  geschlecht: string | null;
  format: string;
  sha256: string;
};

const SEX: Record<string, string> = { M: "Männer", W: "Frauen" };
const BREAK = 2020;
/** short, complete labels for the bars (the full names stay in the table) */
const SHORT_KIND: Record<string, string> = { ALTER: "Alterspensionen", GEM: "Geminderte Arbeitsfähigkeit", WIT: "Witwen/Witwer", WAI: "Waisen" };
const LEVEL_ORDER = ["Gesamt", "Gruppe", "Träger", "Versicherungsbereich"];

export default function PensionsPage() {
  const p = useApi<Pensions>("/api/pensionen");
  return (
    <PageShell wide>
      <PageHeading
        title="Pensionen"
        description="Pensionsstatistik (Tabellen 12 und 13 der Jahresergebnisse) aus den Excel-Meldungen der Pensionsversicherungsträger 2018–2025. Jede Zahl ist bis zur gelieferten Zelle (Datei, Blatt, Zelle, SHA-256) nachvollziehbar."
      />
      {p.error ? (
        <ErrorState error={p.error} onRetry={p.reload} what="Pensionsstatistik" />
      ) : !p.data ? (
        <LoadingState rows={6} />
      ) : (
        <Suspense fallback={<LoadingState rows={6} />}>
          <Body data={p.data} />
        </Suspense>
      )}
    </PageShell>
  );
}

function Body({ data }: { data: Pensions }) {
  const years = useMemo(() => [...new Set(data.values.map((v) => v.jahr))].sort(), [data.values]);
  const carrierName = useMemo(() => new Map(data.carriers.map((c) => [c.code, c.bezeichnung])), [data.carriers]);
  const typeName = useMemo(() => new Map(data.types.map((c) => [c.code, c.bezeichnung])), [data.types]);
  const idx = useMemo(() => {
    const m = new Map<string, PValue>();
    for (const v of data.values) m.set(`${v.jahr}|${v.versicherungstraeger}|${v.pensionsart}|${v.geschlecht}|${v.variable}`, v);
    return m;
  }, [data.values]);
  const get = (j: number, t: string, a: string, g: string, variable = "Pensionen") => idx.get(`${j}|${t}|${a}|${g}|${variable}`);
  const [sex, setSex] = useState("W");
  const [view, setView] = useState<"einzeln" | "vergleich">("einzeln");
  const params = useSearchParams();
  const qT = params.get("traeger");
  const qJ = Number(params.get("jahr"));
  const [carrier, setCarrier] = useState(qT && data.carriers.some((c) => c.code === qT) ? qT : "PV");
  const [year, setYear] = useState(years.includes(qJ) ? qJ : years[years.length - 1]);
  /** years in which the carrier has any value (a reported number or a status such as „nicht gemeldet“) */
  const carrierYears = (code: string) => [...new Set(data.values.filter((v) => v.versicherungstraeger === code).map((v) => v.jahr))].sort();
  const cy = carrierYears(carrier);
  // fallback: nearest year with data (prefer the latest earlier one) – shown with a notice, never silently
  const effYear: number | null = cy.includes(year) ? year : cy.length ? ([...cy].reverse().find((j) => j < year) ?? cy[0]) : null;
  const Y = effYear ?? year;
  const carrierEntry = data.carriers.find((c) => c.code === carrier);
  const [cells, setCells] = useState<{ jahr: number; traeger: string; art?: string; sex?: string } | null>(null);
  const carriersSorted = [...data.carriers].sort((a, b) => LEVEL_ORDER.indexOf(a.ebene) - LEVEL_ORDER.indexOf(b.ebene) || a.code.localeCompare(b.code));
  const t12 = data.types.filter((t) => t.attribute?.tabelle === 12).sort((a, b) => (a.uebergeordnet ? 1 : 0) - (b.uebergeordnet ? 1 : 0));
  const t13 = data.types.filter((t) => t.attribute?.tabelle === 13).sort((a, b) => (a.uebergeordnet ? 1 : 0) - (b.uebergeordnet ? 1 : 0));
  const traeger = data.carriers.filter((c) => c.ebene === "Träger").map((c) => c.code);
  const breakMarker = [{ x: String(BREAK), label: "Bruch 2020", tone: "warning" as const, note: data.description.fussnoten ?? undefined }];

  const runChips = (jahr?: number, traegerCode?: string) => (
    <div className="flex flex-wrap items-center gap-1.5">
      {data.run && (
        <Link
          href={`/laeufe?lauf=${data.run.run_id}`}
          className="inline-flex h-5 items-center gap-1 rounded-full border border-border px-2 text-xs font-medium hover:bg-muted"
          title={`Lauf ${data.run.run_id} öffnen · Prüfsumme ${data.run.checksum}`}
        >
          <HugeiconsIcon icon={PlayCircleIcon} strokeWidth={2} className="size-3" />
          Lauf {data.run.run_id} · {shortHash(data.run.checksum, 10)}
        </Link>
      )}
      {jahr && traegerCode && (
        <Button
          variant="outline"
          size="xs"
          className="h-5 gap-1 rounded-full px-2 text-xs [&_svg]:size-3"
          onClick={() => setCells({ jahr, traeger: traegerCode })}
          aria-label={`Gelieferte Zellen ${traegerCode} ${jahr} anzeigen`}
        >
          <HugeiconsIcon icon={FileSecurityIcon} strokeWidth={2} />
          Zellen {traegerCode} {jahr}
        </Button>
      )}
    </div>
  );

  const seriesChart = (codes: string[], art = "GES", variable = "Pensionen") => ({
    kind: "line" as const,
    x: "jahr",
    series: codes.map((c) => ({ key: c.replace(/[^A-Za-z0-9]/g, "_"), label: c, title: carrierName.get(c) })),
    data: years.map((j) => ({
      jahr: String(j),
      ...Object.fromEntries(codes.map((c) => [c.replace(/[^A-Za-z0-9]/g, "_"), get(j, c, art, sex, variable)?.wert ?? null])),
    })),
    markers: breakMarker,
  });

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <ToggleGroup type="single" value={sex} onValueChange={(v) => v && setSex(v)} variant="outline" size="sm" aria-label="Geschlecht">
          <ToggleGroupItem value="W" className="px-3">
            Frauen
          </ToggleGroupItem>
          <ToggleGroupItem value="M" className="px-3">
            Männer
          </ToggleGroupItem>
        </ToggleGroup>
        <ToggleGroup type="single" value={view} onValueChange={(v) => v && setView(v as "einzeln" | "vergleich")} variant="outline" size="sm" aria-label="Darstellung">
          <ToggleGroupItem value="einzeln" className="px-3">
            Entwicklung je Reihe
          </ToggleGroupItem>
          <ToggleGroupItem value="vergleich" className="px-3">
            Vergleich auf einer Achse
          </ToggleGroupItem>
        </ToggleGroup>
        <span className="text-xs text-muted-foreground">
          {view === "einzeln" ? "jede Reihe mit eigener Achse (beginnt nicht bei 0) – kleine Veränderungen werden sichtbar" : "alle Reihen auf einer Achse ab 0 – Größenvergleich"} · gilt für die beiden Zeitreihen
        </span>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title={`Pensionen insgesamt – ${SEX[sex]}`} description="Tabelle 12, Jahresdurchschnitt; PV insgesamt sowie Unselbständige und Selbständige (berechnet aus den Meldungen).">
          {view === "vergleich" ? (
            <StatChart spec={seriesChart(["PV", "PV-UNS", "PV-SELB"])} height={260} />
          ) : (
            <SmallMultiples spec={seriesChart(["PV", "PV-UNS", "PV-SELB"])} />
          )}
          {runChips()}
        </Panel>
        <Panel
          title={`Pensionen je Träger – ${SEX[sex]}`}
          description={
            <span>
              <span className="text-warning">
                Zeitreihenbruch 2020: <Abbr code="SVA" names={carrierName} /> + <Abbr code="SVB" names={carrierName} /> + <Abbr code="VAN" names={carrierName} /> →{" "}
                <Abbr code="SVS" names={carrierName} />, <Abbr code="VAEB" names={carrierName} /> → <Abbr code="BVAEB" names={carrierName} />.
              </span>{" "}
              Lücken = Träger bestand in dem Jahr nicht. Namen beim Überfahren der Kürzel.
            </span>
          }
        >
          {view === "vergleich" ? <StatChart spec={seriesChart(traeger)} height={260} /> : <SmallMultiples spec={seriesChart(traeger)} />}
          {runChips()}
        </Panel>
      </div>

      <div className="sticky top-[49px] z-10 -mx-1 flex flex-wrap items-center gap-2 rounded-xl border border-border bg-background/95 px-3 py-2 backdrop-blur">
        <span className="text-sm font-medium">Je Versicherungsträger</span>
        <Select value={carrier} onValueChange={setCarrier}>
          <SelectTrigger size="sm" className="w-80" aria-label="Versicherungsträger">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {carriersSorted.map((c) => (
              <SelectItem key={c.code} value={c.code}>
                {c.code} – {c.bezeichnung}
                {carrierYears(c.code).length > 0 && carrierYears(c.code).length < years.length
                  ? ` (${carrierYears(c.code)[0]}–${carrierYears(c.code).at(-1)})`
                  : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={String(year)} onValueChange={(v) => setYear(Number(v))}>
          <SelectTrigger size="sm" className="w-44" aria-label="Jahr">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {years.map((j) => (
              <SelectItem key={j} value={String(j)}>
                {j}
                {!carrierYears(carrier).includes(j) ? " (keine Daten)" : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground">gilt für Pensionsart × Geschlecht und Tabelle 13</span>
      </div>
      {effYear !== year && (
        <div role="status" className="-mt-2 rounded-xl border border-warning/40 bg-warning/10 px-3 py-2 text-sm text-warning">
          Für {carrier} ({carrierName.get(carrier)}) gibt es für {year} keine Daten
          {carrierEntry?.gueltig_bis ? ` – der Träger bestand nur bis ${fmtDate(carrierEntry.gueltig_bis)}` : ""}
          {carrierEntry?.gueltig_von && Number(carrierEntry.gueltig_von.slice(0, 4)) > year ? ` – der Träger besteht erst ab ${fmtDate(carrierEntry.gueltig_von)}` : ""}.
          Gezeigt wird stattdessen <span className="font-medium">{effYear}</span> (nächstes Jahr mit Daten).
        </div>
      )}
      {effYear === null && (
        <div role="status" className="-mt-2 rounded-xl border border-border bg-muted px-3 py-2 text-sm text-muted-foreground">
          Für {carrier} liegen keine Werte vor.
        </div>
      )}

      <Panel
        title={`Pensionsart × Geschlecht · ${carrier} · ${effYear ?? year}`}
        description={`${carrierName.get(carrier) ?? carrier} – Tabelle 12. Werte anklicken: gelieferte Zellen.`}
      >
        <div className="grid gap-4 2xl:grid-cols-2">
          <div className="flex flex-col gap-3">
            {/* the computed total is a KPI, not a bar – as a bar it dominated the scale and hid the smaller kinds */}
            {t12.filter((t) => !t.uebergeordnet).map((t) => (
              <div key={t.code} className="flex flex-wrap items-baseline gap-x-4 gap-y-1 rounded-xl border border-border px-3 py-2">
                <span className="text-xs text-muted-foreground">{typeName.get(t.code)} (berechnet)</span>
                {["M", "W"].map((g) => (
                  <span key={g} className="text-sm">
                    {SEX[g]} <span className="font-mono font-medium tabular-nums">{fmt(get(Y, carrier, t.code, g)?.wert)}</span>
                  </span>
                ))}
              </div>
            ))}
            <StatChart
              height={200}
              spec={{
                kind: "hbar",
                x: "art",
                series: [
                  { key: "M", label: "Männer" },
                  { key: "W", label: "Frauen" },
                ],
                data: t12
                  .filter((t) => t.uebergeordnet)
                  .map((t) => ({ art: SHORT_KIND[t.code] ?? typeName.get(t.code) ?? t.code, M: get(Y, carrier, t.code, "M")?.wert ?? null, W: get(Y, carrier, t.code, "W")?.wert ?? null })),
              }}
            />
          </div>
          <div className="overflow-x-auto rounded-xl border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Pensionsart</TableHead>
                  <TableHead className="text-right text-xs">Männer</TableHead>
                  <TableHead className="text-right text-xs">Frauen</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {t12.map((t) => (
                  <TableRow key={t.code}>
                    <TableCell className={cn("text-xs", !t.uebergeordnet && "font-medium")}>
                      {typeName.get(t.code)} {Boolean(t.attribute?.berechnet) && <span className="text-muted-foreground">(berechnet)</span>}
                    </TableCell>
                    {["M", "W"].map((g) => (
                      <TableCell key={g} className="text-right">
                        <ValueButton v={get(Y, carrier, t.code, g)} onClick={() => setCells({ jahr: Y, traeger: carrier, art: t.code, sex: g })} />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
        {runChips(Y, carrier)}
      </Panel>

      <Table13 years={years} carrier={carrier} t13={t13} typeName={typeName} get={get} onCell={(j, art, g) => setCells({ jahr: j, traeger: carrier, art, sex: g })} />

      <SectionTitle>Versicherungsträger (klass_versicherungstraeger)</SectionTitle>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
        <Panel title="Hierarchie und Gültigkeit">
          <CarrierTree carriers={data.carriers} />
        </Panel>
        <Panel
          title="Übergänge 2020 (Zusammenlegungen)"
          description="Links die Träger und Bereiche, die bis 31.12.2019 gemeldet haben (Meldungen 2018–2019), rechts die ab 01.01.2020 (Meldungen 2020–2025). Pfeile zeigen, wohin ein Träger übergegangen ist: n:1 = mehrere Träger zu einem zusammengelegt, 1:1 = als Bereich unverändert weitergeführt."
        >
          <TransitionGraph explanation={transitionGraph(data.transitions, carrierName)} height={320} />
          <div className="flex flex-col divide-y divide-border rounded-xl border border-border">
            {data.transitions.map((t, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: transitions have no id
              <div key={i} className="grid grid-cols-[minmax(0,11rem)_auto_minmax(0,1fr)] items-center gap-3 px-3 py-2 text-xs">
                <span className="flex items-center gap-1.5 font-mono">
                  <span className="text-muted-foreground">{t.code_alt}</span>
                  <span aria-hidden>→</span>
                  <span className="font-medium text-foreground">{t.code_neu}</span>
                </span>
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-[10px] font-medium",
                    t.beziehung === "n:1" ? "bg-warning/10 text-warning" : "bg-muted text-muted-foreground",
                  )}
                >
                  {t.beziehung === "n:1" ? "zusammengelegt" : "weitergeführt"} · ab {fmtDate(t.gueltig_ab)}
                </span>
                <span className="text-muted-foreground">{t.anmerkung}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <details>
        <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
          <HugeiconsIcon icon={DatabaseIcon} strokeWidth={2} className="mr-1 inline size-3.5" />
          Abfrage (stat_pensionen)
        </summary>
        <SqlBlock code={data.sql} className="mt-2" />
      </details>

      <CellsSheet req={cells} onClose={() => setCells(null)} carrierName={carrierName} />
    </>
  );
}

/** Carrier code with its full name on hover. */
function Abbr({ code, names }: { code: string; names: Map<string, string> }) {
  return (
    <Tooltip delayDuration={0}>
      <TooltipTrigger asChild>
        <abbr tabIndex={0} className="font-mono no-underline decoration-dotted underline-offset-4 outline-none hover:underline">
          {code}
        </abbr>
      </TooltipTrigger>
      <TooltipContent>{names.get(code) ?? code}</TooltipContent>
    </Tooltip>
  );
}

/** One small line chart per series, each with its own zoomed axis – shows small changes that vanish on a shared axis. */
function SmallMultiples({ spec }: { spec: ChartSpec }) {
  const withData = spec.series.filter((s) => spec.data.some((d) => typeof d[s.key] === "number"));
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {withData.map((s) => {
        const vals = spec.data.map((d) => d[s.key]).filter((v): v is number => typeof v === "number");
        const first = vals[0];
        const last = vals[vals.length - 1];
        return (
          <div key={s.key} className="flex flex-col gap-1 rounded-xl border border-border p-2.5">
            <div className="flex items-baseline justify-between gap-2 text-xs">
              <Tooltip delayDuration={0}>
                <TooltipTrigger asChild>
                  <span tabIndex={0} className="font-mono font-medium underline decoration-dotted underline-offset-4 outline-none">
                    {s.label}
                  </span>
                </TooltipTrigger>
                <TooltipContent>{s.title ?? s.label}</TooltipContent>
              </Tooltip>
              <span className="text-muted-foreground tabular-nums">
                {fmt(last)}
                {vals.length > 1 && first ? (
                  <span className={cn("ml-1.5", last >= first ? "text-success" : "text-destructive")}>
                    {last >= first ? "+" : "−"}
                    {fmt(Math.abs(((last - first) / first) * 100), 1)} %
                  </span>
                ) : null}
              </span>
            </div>
            <StatChart height={110} spec={{ ...spec, series: [s] }} />
          </div>
        );
      })}
    </div>
  );
}

function ValueButton({ v, onClick }: { v?: PValue; onClick: () => void }) {
  if (!v) return <span className="font-mono text-xs text-muted-foreground">–</span>;
  if (v.wert === null)
    return (
      <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground" title={v.stand}>
        {v.status}
      </span>
    );
  return (
    <button
      type="button"
      onClick={onClick}
      title={`${v.stand} · ${v.status} – gelieferte Zellen anzeigen`}
      className="font-mono text-xs tabular-nums underline decoration-dotted underline-offset-4 hover:decoration-solid"
    >
      {fmt(v.wert)}
    </button>
  );
}

function Table13({
  years,
  carrier,
  t13,
  typeName,
  get,
  onCell,
}: {
  years: number[];
  carrier: string;
  t13: KEntry[];
  typeName: Map<string, string>;
  get: (j: number, t: string, a: string, g: string, variable?: string) => PValue | undefined;
  onCell: (j: number, art: string, g: string) => void;
}) {
  const V = "VorzeitigeAlterspensionen";
  return (
    <Panel
      title={`Tabelle 13 – vorzeitige Alterspensionen · ${carrier}`}
      description={
        <span className="flex flex-col gap-1.5">
          <span className="w-fit rounded-md bg-warning/10 px-2 py-1 text-warning">
            Hervorgehoben: Sprung auf 0 oder mindestens Verdreifachung gegenüber dem Vorjahr.
          </span>
          <span>
            Solche Sprünge bei SA1/SA2 sind Folgen von Gesetzesänderungen (RD-04), keine Datenfehler – sie werden nicht korrigiert. „nicht gemeldet“
            ist kein Nullwert.
          </span>
        </span>
      }
    >
      <div className="overflow-x-auto rounded-xl border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-xs">Art</TableHead>
              <TableHead className="text-xs">Geschl.</TableHead>
              {years.map((j) => (
                <TableHead key={j} className={cn("text-right text-xs", j === BREAK && "border-l border-warning/50")}>
                  {j}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {t13.flatMap((t) =>
              ["M", "W"].map((g) => (
                <TableRow key={`${t.code}-${g}`}>
                  {g === "M" && (
                    <TableCell rowSpan={2} className={cn("align-top text-xs", !t.uebergeordnet && "font-medium")}>
                      <span className="font-mono">{t.code}</span> {typeName.get(t.code)}
                    </TableCell>
                  )}
                  <TableCell className="text-xs text-muted-foreground">{g === "M" ? "M" : "W"}</TableCell>
                  {years.map((j, i) => {
                    const v = get(j, carrier, t.code, g, V);
                    const prev = i > 0 ? get(years[i - 1], carrier, t.code, g, V)?.wert : null;
                    const jump =
                      v?.wert !== null &&
                      v?.wert !== undefined &&
                      prev !== null &&
                      prev !== undefined &&
                      ((prev > 0 && v.wert === 0) || (prev > 0 && v.wert >= prev * 3) || (prev === 0 && v.wert >= 50));
                    return (
                      <TableCell key={j} className={cn("text-right", jump && "bg-warning/10", j === BREAK && "border-l border-warning/50")}>
                        {v?.wert === null ? (
                          <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] whitespace-nowrap text-muted-foreground">nicht gemeldet</span>
                        ) : (
                          <ValueButton v={v} onClick={() => onCell(j, t.code, g)} />
                        )}
                      </TableCell>
                    );
                  })}
                </TableRow>
              )),
            )}
          </TableBody>
        </Table>
      </div>
    </Panel>
  );
}

function CarrierTree({ carriers }: { carriers: KEntry[] }) {
  const children = (parent: string | null) => carriers.filter((c) => c.uebergeordnet === parent).sort((a, b) => a.code.localeCompare(b.code));
  const render = (c: KEntry, depth: number): React.ReactNode => (
    <li key={c.code} className="flex flex-col">
      <div className="flex flex-wrap items-baseline gap-x-2 py-1 text-sm" style={{ paddingLeft: depth * 16 }}>
        <span className="font-mono text-xs font-medium">{c.code}</span>
        <span className={cn(c.gueltig_bis && "text-muted-foreground")}>{c.bezeichnung}</span>
        <span className="text-[11px] text-muted-foreground">
          {c.ebene}
          {(c.gueltig_von || c.gueltig_bis) && ` · ${c.gueltig_von ? fmtDate(c.gueltig_von) : "…"} – ${c.gueltig_bis ? fmtDate(c.gueltig_bis) : "offen"}`}
        </span>
      </div>
      {children(c.code).length > 0 && <ul>{children(c.code).map((x) => render(x, depth + 1))}</ul>}
    </li>
  );
  return <ul className="flex flex-col">{children(null).map((c) => render(c, 0))}</ul>;
}

function transitionGraph(edges: KlassEdge[], names: Map<string, string>): KlassExplanation {
  // column labels sort in time order (the graph orders columns by label) → old left, new right, edges point inwards
  const OLD = "2018–2019";
  const NEW = "2020–2025";
  const mapped = edges.map((e) => ({ ...e, version_alt: OLD, version_neu: NEW }));
  const nodes = new Map<string, { id: string; version: string; code: string; label: string }>();
  for (const e of mapped) {
    nodes.set(`${OLD}|${e.code_alt}`, { id: `${OLD}|${e.code_alt}`, version: OLD, code: e.code_alt, label: names.get(e.code_alt) ?? "" });
    nodes.set(`${NEW}|${e.code_neu}`, { id: `${NEW}|${e.code_neu}`, version: NEW, code: e.code_neu, label: names.get(e.code_neu) ?? "" });
  }
  return { text: "", edges: mapped, nodes: [...nodes.values()] };
}

function CellsSheet({
  req,
  onClose,
  carrierName,
}: {
  req: { jahr: number; traeger: string; art?: string; sex?: string } | null;
  onClose: () => void;
  carrierName: Map<string, string>;
}) {
  const cells = useApi<{ cells: Cell[] }>(req ? `/api/pensionen/zellen?jahr=${req.jahr}&traeger=${encodeURIComponent(req.traeger)}` : null);
  const [mode, setMode] = useState<"geliefert" | "gelesen">("geliefert");
  const [onlyMatch, setOnlyMatch] = useState(true);
  useEffect(() => setOnlyMatch(true), [req]);
  const isMatch = (c: Cell) => !!req?.art && c.pensionsart === req.art && (!req.sex || c.geschlecht === req.sex);
  const all = cells.data?.cells ?? [];
  const matches = all.filter(isMatch);
  const rows = onlyMatch && matches.length ? matches : all;
  const files = [...new Map(all.map((c) => [c.path, c.sha256])).entries()];
  return (
    <Sheet open={req !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-2xl">
        <SheetHeader className="gap-1 border-b border-border p-5 pr-12 text-left">
          <SheetDescription className="text-xs font-medium">Quellennachweis · gelieferte Zellen</SheetDescription>
          <SheetTitle className="text-lg">
            {req?.traeger} {req?.jahr}
            {req?.art ? ` · ${req.art}${req.sex ? ` · ${SEX[req.sex]}` : ""}` : ""}
          </SheetTitle>
          <p className="text-xs text-muted-foreground">{req && carrierName.get(req.traeger)}</p>
        </SheetHeader>
        <div className="flex flex-col gap-4 p-5">
          {cells.error ? (
            <ErrorState error={cells.error} what="Zellen" />
          ) : !cells.data ? (
            <LoadingState rows={4} />
          ) : all.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Keine gelieferten Zellen für {req?.traeger} {req?.jahr} – der Wert ist berechnet (Summe der Träger bzw. Bereiche, siehe Abfrage). Die Zellen
              stehen bei den einzelnen Trägern.
            </p>
          ) : (
            <>
              <div className="flex flex-col gap-1.5">
                {files.map(([path, sha]) => (
                  <div key={path} className="flex flex-wrap items-center gap-2 rounded-xl border border-border px-3 py-2 text-xs">
                    <span className="font-mono">{path}</span>
                    <span className="ml-auto flex items-center gap-1 font-mono text-muted-foreground" title={sha}>
                      SHA-256 {shortHash(sha, 16)}
                      <CopyButton text={sha} label="SHA-256 kopieren" />
                    </span>
                  </div>
                ))}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <ToggleGroup type="single" value={mode} onValueChange={(v) => v && setMode(v as "geliefert" | "gelesen")} size="sm" variant="outline" aria-label="Darstellung">
                  <ToggleGroupItem value="geliefert" className="px-3">
                    wie geliefert
                  </ToggleGroupItem>
                  <ToggleGroupItem value="gelesen" className="px-3">
                    wie gelesen
                  </ToggleGroupItem>
                </ToggleGroup>
                {matches.length > 0 && (
                  <Button variant="ghost" size="xs" onClick={() => setOnlyMatch((x) => !x)}>
                    {onlyMatch ? `alle ${all.length} Zellen zeigen` : "nur passende Zellen"}
                  </Button>
                )}
              </div>
              <div className="overflow-x-auto rounded-xl border border-border">
                <Table>
                  <TableHeader>
                    {mode === "geliefert" ? (
                      <TableRow>
                        <TableHead className="text-xs">Blatt!Zelle</TableHead>
                        <TableHead className="text-xs">Bereich</TableHead>
                        <TableHead className="text-xs">Art</TableHead>
                        <TableHead className="text-xs">Geschlecht</TableHead>
                        <TableHead className="text-right text-xs">Zelltext</TableHead>
                      </TableRow>
                    ) : (
                      <TableRow>
                        <TableHead className="text-xs">Tabelle</TableHead>
                        <TableHead className="text-xs">Träger</TableHead>
                        <TableHead className="text-xs">Pensionsart</TableHead>
                        <TableHead className="text-xs">Geschl.</TableHead>
                        <TableHead className="text-right text-xs">Wert</TableHead>
                      </TableRow>
                    )}
                  </TableHeader>
                  <TableBody>
                    {rows.map((c) => (
                      <TableRow key={`${c.path}|${c.sheet}|${c.cell_ref}`} className={cn(isMatch(c) && !onlyMatch && "bg-warning/10")}>
                        {mode === "geliefert" ? (
                          <>
                            <TableCell className="font-mono text-xs whitespace-nowrap">
                              {c.sheet}!{c.cell_ref}
                            </TableCell>
                            <TableCell className="text-xs">{c.bereich_raw || <span className="text-muted-foreground">leer</span>}</TableCell>
                            <TableCell className="max-w-40 truncate text-xs" title={c.art_raw}>
                              {c.art_raw || <span className="text-muted-foreground">leer</span>}
                            </TableCell>
                            <TableCell className="text-xs">{c.geschlecht_raw || <span className="text-muted-foreground">leer</span>}</TableCell>
                            <TableCell className="text-right font-mono text-xs">„{c.raw_value}“</TableCell>
                          </>
                        ) : (
                          <>
                            <TableCell className="font-mono text-xs">{c.tabelle}</TableCell>
                            <TableCell className="font-mono text-xs">{c.versicherungstraeger ?? "–"}</TableCell>
                            <TableCell className="font-mono text-xs">{c.pensionsart ?? <span className="text-muted-foreground">Summe</span>}</TableCell>
                            <TableCell className="font-mono text-xs">{c.geschlecht ?? "–"}</TableCell>
                            <TableCell className="text-right font-mono text-xs tabular-nums">{fmt(c.value)}</TableCell>
                          </>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <p className="text-[11px] text-muted-foreground">Format der Meldung: {[...new Set(all.map((c) => c.format))].join(", ")}. Zellen ohne Pensionsart sind gemeldete Summen (Summenprüfung).</p>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
