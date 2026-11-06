"use client";

import { Alert02Icon, RefreshIcon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useMemo, useState } from "react";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export type QualityOption = {
  id: string;
  label: string;
  definition: string;
  action: string;
  is_default: boolean;
  available: boolean;
  reason: string | null;
};

export type QualityIssue = {
  problem_id: string;
  title: string;
  severity: "hoch" | "mittel" | "niedrig" | string;
  affected: number;
  months: string[];
  description: string;
  options: QualityOption[];
  default: string;
  chosen: string;
  free_text: string;
};

export type QualityHandling = {
  copy_id: string;
  applied: { problem_id: string; option_id: string; label: string; action: string; removed: number; added: number; default: boolean }[];
  hidden_months: string[];
  notes: string[];
  sql: string;
};

export type Quality = { issues: QualityIssue[]; handling: QualityHandling | null };

const SEVERITY: Record<string, string> = {
  hoch: "bg-destructive/10 text-destructive",
  mittel: "bg-warning/10 text-warning",
  niedrig: "bg-secondary text-muted-foreground",
};

/**
 * Data-quality panel of a StatCard: every known problem in the fields the number needs, with three ways to handle it.
 * The default is the approved rule; anything else recalculates on a copy (work.dq_copy) and is never an official number.
 */
export function QualityPanel({
  quality,
  onRecalc,
  disabled,
}: {
  quality: Quality;
  onRecalc?: (handling: Record<string, string>, freeText: Record<string, string>, summary: string) => void;
  disabled?: boolean;
}) {
  const init = useMemo(
    () => ({
      sel: Object.fromEntries(quality.issues.map((i) => [i.problem_id, i.chosen ?? i.default])),
      text: Object.fromEntries(quality.issues.map((i) => [i.problem_id, i.free_text ?? ""])),
    }),
    [quality],
  );
  const [sel, setSel] = useState<Record<string, string>>(init.sel);
  const [text, setText] = useState<Record<string, string>>(init.text);
  const main = quality.issues.filter((i) => i.severity !== "niedrig");
  const minor = quality.issues.filter((i) => i.severity === "niedrig");
  const changed = quality.issues.some((i) => sel[i.problem_id] !== init.sel[i.problem_id] || (text[i.problem_id] ?? "") !== (init.text[i.problem_id] ?? ""));

  if (!quality.issues.length) return null;

  const submit = () => {
    if (!onRecalc) return;
    const handling: Record<string, string> = {};
    const freeText: Record<string, string> = {};
    const parts: string[] = [];
    for (const i of quality.issues) {
      const v = sel[i.problem_id];
      if (v && v !== i.default) {
        handling[i.problem_id] = v;
        parts.push(`${i.problem_id} → ${i.options.find((o) => o.id === v)?.label ?? v}`);
      }
      const t = (text[i.problem_id] ?? "").trim();
      if (t) {
        freeText[i.problem_id] = t;
        parts.push(`${i.problem_id}: „${t}“`);
      }
    }
    onRecalc(handling, freeText, parts.join(" · ") || "Standardbehandlung (freigegebene Regeln)");
  };

  const renderIssue = (i: QualityIssue) => (
    <div key={i.problem_id} className="flex flex-col gap-2 rounded-xl border border-border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge className={cn("shrink-0", SEVERITY[i.severity] ?? SEVERITY.niedrig)}>{i.severity}</Badge>
        <span className="font-mono text-xs">{i.problem_id}</span>
        <span className="text-sm font-medium">{i.title}</span>
        <span className="ml-auto font-mono text-xs text-muted-foreground tabular-nums">{fmt(i.affected)} betroffen</span>
      </div>
      <p className="text-xs text-muted-foreground">{i.description}</p>
      <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label={`Behandlung ${i.problem_id}`}>
        {i.options.map((o) => {
          const active = sel[i.problem_id] === o.id;
          const chip = (
            <button
              type="button"
              role="radio"
              aria-checked={active}
              disabled={!o.available || !onRecalc}
              onClick={() => setSel((s) => ({ ...s, [i.problem_id]: o.id }))}
              className={cn(
                "flex flex-col items-start rounded-xl border px-2.5 py-1.5 text-left text-xs transition-colors disabled:cursor-not-allowed disabled:opacity-50",
                active ? "border-foreground/40 bg-gray-alpha-150" : "border-border hover:bg-muted",
              )}
            >
              <span className="font-medium">
                {o.label}
                {o.is_default && <span className="font-normal text-muted-foreground"> · Standard – freigegebene Regel</span>}
              </span>
            </button>
          );
          return (
            <Tooltip key={o.id}>
              <TooltipTrigger asChild>
                {/* span keeps the tooltip working on disabled buttons */}
                <span className="inline-flex">{chip}</span>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">{!o.available && o.reason ? `Nicht verfügbar: ${o.reason}` : o.definition}</TooltipContent>
            </Tooltip>
          );
        })}
      </div>
      <Input
        value={text[i.problem_id] ?? ""}
        onChange={(e) => setText((t) => ({ ...t, [i.problem_id]: e.target.value }))}
        placeholder="Eigene Behandlung beschreiben …"
        aria-label={`Eigene Behandlung für ${i.problem_id} beschreiben`}
        className="h-8 text-xs"
        disabled={!onRecalc}
        maxLength={300}
      />
    </div>
  );

  return (
    <section className="flex flex-col gap-2 rounded-2xl border border-dashed border-border p-3" aria-label="Datenqualität">
      <div className="flex items-center gap-2 text-xs font-medium">
        <HugeiconsIcon icon={Alert02Icon} strokeWidth={2} className="size-3.5 text-warning" />
        Datenqualität der verwendeten Felder ({quality.issues.length})
        <span className="font-normal text-muted-foreground">– Standard ist die freigegebene Regel; Alternativen rechnen auf einer Kopie.</span>
      </div>
      {main.map(renderIssue)}
      {minor.length > 0 && (
        <details>
          <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">weitere Hinweise ({minor.length})</summary>
          <div className="mt-2 flex flex-col gap-2">{minor.map(renderIssue)}</div>
        </details>
      )}
      {onRecalc && (
        <Button size="sm" variant={changed ? "default" : "outline"} className="w-fit" disabled={disabled || !changed} onClick={submit}>
          <HugeiconsIcon icon={RefreshIcon} strokeWidth={2} data-icon="inline-start" />
          Mit dieser Behandlung neu berechnen
        </Button>
      )}
    </section>
  );
}
