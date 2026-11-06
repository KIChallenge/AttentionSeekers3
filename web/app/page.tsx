"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useApi } from "@/hooks/use-api";
import { useDqMarkers } from "@/hooks/use-markers";
import { ApiError, apiPost } from "@/lib/api";
import { fmtMonth } from "@/lib/format";
import type { Overview, StatResult } from "@/lib/types";
import { AnimatedNumber } from "@/components/stat/animated-number";
import { PageHeading, PageShell } from "@/components/stat/page-shell";
import { StatCard } from "@/components/stat/stat-card";
import { ErrorState, LoadingState } from "@/components/stat/states";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const TILES: { key: keyof Overview["stats"]; label: string; href: string }[] = [
  { key: "deliveries", label: "Monatslieferungen", href: "/lieferungen" },
  { key: "rows", label: "gelieferte Sätze", href: "/lieferungen" },
  { key: "files", label: "Paketdateien (SHA-256)", href: "/lieferungen" },
  { key: "runs_done", label: "abgeschlossene Läufe", href: "/laeufe" },
  { key: "rules_approved", label: "Regeln freigegeben", href: "/freigaben" },
  { key: "rules_proposed", label: "Regeln warten auf Freigabe", href: "/freigaben" },
  { key: "findings", label: "Befunde in Qualitätsberichten", href: "/qualitaetsberichte" },
  { key: "klass_entries", label: "Klassifikationseinträge", href: "/klassifikationen" },
];

export default function OverviewPage() {
  const overview = useApi<Overview>("/api/overview");
  const months = useApi<{ months: string[] }>("/api/statistik/monate?regelwerk=basis");
  const markers = useDqMarkers();
  const [series, setSeries] = useState<StatResult | null>(null);
  const [seriesError, setSeriesError] = useState<ApiError | null>(null);

  useEffect(() => {
    if (!months.data?.months.length) return;
    apiPost<StatResult>("/api/statistik", { regelwerk: "basis", monate: months.data.months, dimensionen: [], kennzahl: "bestand" })
      .then(setSeries)
      .catch((e) => setSeriesError(e instanceof ApiError ? e : new ApiError(0, String(e))));
  }, [months.data]);

  const last = series?.rows[series.rows.length - 1];
  const prev = series?.rows[series.rows.length - 2];
  const chart = useMemo(
    () =>
      series && {
        kind: "line" as const,
        x: "monat",
        series: [{ key: "wert", label: "Beschäftigungsverhältnisse" }],
        data: series.rows.map((r) => ({ monat: r.monat, wert: r.wert })),
        markers: markers.map((m) => ({ x: m.x, label: `${m.label}${m.status === "approved" ? "" : " ?"}`, tone: m.tone })),
      },
    [series, markers],
  );

  return (
    <PageShell>
      <PageHeading
        title="Übersicht"
        description="Amtliche Beschäftigungsstatistik aus den Monatslieferungen des ZVD – deterministisch aus SQL gerechnet, jede Zahl mit Quellennachweis, jede Regel von einer namentlich genannten Person freigegeben."
      />
      {overview.error ? (
        <ErrorState error={overview.error} what="Übersicht" onRetry={overview.reload} />
      ) : !overview.data ? (
        <LoadingState rows={2} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {TILES.map((t) => (
            <Link key={t.key} href={t.href} className="rounded-2xl outline-offset-2 focus-visible:outline-1">
              <Card className="h-full gap-3 rounded-2xl border border-gray-alpha-150 bg-card p-4 shadow-none ring-0 transition-colors hover:bg-muted">
                <CardHeader className="gap-3 p-0">
                  <CardDescription className="min-h-10 font-medium">{t.label}</CardDescription>
                  <CardTitle className="text-3xl font-medium tabular-nums text-foreground">
                    <AnimatedNumber value={overview.data?.stats[t.key] ?? 0} />
                  </CardTitle>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      )}
      {seriesError ? (
        <ErrorState error={seriesError} what="Zeitreihe" />
      ) : series && chart ? (
        <StatCard
          title="Beschäftigungsverhältnisse am Stichtag"
          definition={series.definition}
          kpis={[
            { label: `Stand ${fmtMonth(last?.monat)}`, value: last?.wert ?? null, delta: last && prev ? last.wert - prev.wert : null },
            { label: "Monate gerechnet", value: series.rows.length },
          ]}
          chart={chart}
          table={{ columns: [{ key: "monat", label: "Monat" }, { key: "wert", label: "Verhältnisse" }], rows: series.rows }}
          sql={series.sql}
          evidence={series.evidence}
          warnings={series.warnings}
          examples={last ? { regelwerk: "basis", monat: last.monat } : null}
          footnote={
            markers.length > 0 && (
              <>
                Markiert:{" "}
                {markers.map((m, i) => (
                  <span key={m.rule}>
                    {i > 0 && " · "}
                    {m.x} {m.label} ({m.rule} {m.status === "approved" ? "freigegeben" : "nur vorgeschlagen, nicht angewendet"})
                  </span>
                ))}
              </>
            )
          }
        />
      ) : (
        <LoadingState label="Zeitreihe wird abgefragt …" rows={4} />
      )}
    </PageShell>
  );
}
