"use client";

import { TestTube01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useEffect, useState } from "react";
import { useApi } from "@/hooks/use-api";
import { useSseJob } from "@/hooks/use-sse-job";
import { fmt, fmtMonth } from "@/lib/format";
import type { QbListItem, Rule, RunMetrics } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ProgressCard } from "./progress-card";

type PreviewResult = { run_id: number; month: string; rule_set: string; rules: string[]; checksum: string; metrics: RunMetrics; findings: unknown[] | number };

/**
 * „Probeweise anwenden“: a month run with the proposed rule as preview (POST /api/laeufe with `vorschau`).
 * The backend rolls the whole run back – no run, no QB file, no approval, no protocol entry. Shows official vs. with rule.
 */
export function TrialApply({ rule }: { rule: Rule }) {
  const months = useApi<{ months: string[] }>(`/api/statistik/monate?regelwerk=${rule.rule_set}`);
  const official = useApi<{ reports: QbListItem[] }>(`/api/qualitaetsberichte?regelwerk=${rule.rule_set}`);
  const ruleMonths = (rule.parameters as { deliveries?: string[] } | null)?.deliveries;
  const [month, setMonth] = useState<string>("");
  useEffect(() => {
    if (month) return;
    const all = months.data?.months ?? [];
    const pref = ruleMonths?.find((m) => all.includes(m)) ?? all[all.length - 1];
    if (pref) setMonth(pref);
  }, [months.data, ruleMonths, month]);
  const job = useSseJob<PreviewResult>();
  const off = official.data?.reports.find((r) => r.month === month);
  const res = job.result;
  const after = res?.metrics?.records_total;
  const before = off?.total;

  return (
    <div className="flex flex-col gap-2 rounded-xl border border-dashed border-info/40 p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-info">Probeweise anwenden</span>
        <span className="text-xs text-muted-foreground">– ohne Freigabe, wird zurückgerollt, kein Protokolleintrag</span>
        <Select value={month} onValueChange={setMonth} disabled={job.status === "running"}>
          <SelectTrigger size="sm" className="ml-auto w-52" aria-label="Monat für die Probe">
            <SelectValue placeholder="Monat" />
          </SelectTrigger>
          <SelectContent>
            {(months.data?.months ?? []).map((m) => (
              <SelectItem key={m} value={m}>
                {fmtMonth(m)}
                {ruleMonths?.includes(m) ? " · betroffen" : ""}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          size="sm"
          variant="outline"
          disabled={!month || job.status === "running"}
          onClick={() => void job.start("/api/laeufe", { lieferung: month, regelwerk: rule.rule_set, vorschau: [rule.rule_id] })}
        >
          <HugeiconsIcon icon={TestTube01Icon} strokeWidth={2} data-icon="inline-start" />
          {job.status === "running" ? "Probe läuft …" : "Probe starten"}
        </Button>
      </div>
      <ProgressCard
        title={`Probe ${rule.rule_id} · ${fmtMonth(month)} (wird zurückgerollt)`}
        status={job.status}
        steps={job.steps.map((s) => ({ step: s.detail ?? s.step, pct: s.pct }))}
        pct={job.pct}
        error={job.error}
      >
        {res && (
          <div className="flex flex-col gap-2 text-sm">
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg border border-border p-2">
                <div className="text-xs text-muted-foreground">offiziell (freigegebene Regeln)</div>
                <div className="font-mono text-lg tabular-nums">{fmt(before)}</div>
              </div>
              <div className="rounded-lg border border-info/40 bg-info/5 p-2">
                <div className="text-xs text-muted-foreground">mit {rule.rule_id} (Probe)</div>
                <div className="font-mono text-lg tabular-nums">{fmt(after)}</div>
              </div>
              <div className="rounded-lg border border-border p-2">
                <div className="text-xs text-muted-foreground">Differenz</div>
                <div className="font-mono text-lg tabular-nums">
                  {before !== undefined && after !== undefined ? `${after - before > 0 ? "+" : ""}${fmt(after - before)}` : "–"}
                </div>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Regeln der Probe: {res.rules?.join(", ")} · Prüfsumme der Probe {res.checksum} · Befunde{" "}
              {Array.isArray(res.findings) ? fmt(res.findings.length) : fmt(res.findings as number)}. Nichts davon wurde gespeichert – die
              offiziellen Zahlen ändern sich erst nach einer Freigabe durch eine Person.
            </p>
          </div>
        )}
      </ProgressCard>
    </div>
  );
}
