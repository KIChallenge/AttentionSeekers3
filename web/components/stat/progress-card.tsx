"use client";

import { Alert02Icon, CheckmarkCircle02Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { AnimatePresence, motion } from "motion/react";
import type { ReactNode } from "react";
import type { ProgressStep } from "@/hooks/use-sse-job";
import { fmt } from "@/lib/format";
import { cn } from "@/lib/utils";
import { FixLinks } from "@/components/stat/fix-links";
import { Shimmer } from "@/components/stat/shimmer";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";

/** Streamed progress „Lieferung 2025-03 wird gelesen … 100 %“ from SSE progress events. */
export function ProgressCard({
  title,
  status,
  steps,
  pct,
  error,
  children,
  elapsedMs,
}: {
  title: string;
  status: "idle" | "running" | "done" | "error";
  steps: ProgressStep[];
  /** null = indeterminate (the stream sends no percentage) */
  pct: number | null;
  error?: string;
  children?: ReactNode;
  elapsedMs?: number;
}) {
  if (status === "idle") return null;
  const last = steps[steps.length - 1];
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <Card className="gap-4 rounded-2xl border border-border bg-card p-4 shadow-none ring-0" aria-live="polite">
        <CardHeader className="flex flex-row items-center gap-2 p-0">
          {status === "running" && <Spinner className="size-4 text-muted-foreground" />}
          {status === "done" && <HugeiconsIcon icon={CheckmarkCircle02Icon} strokeWidth={2} className="size-4 text-success" />}
          {status === "error" && <HugeiconsIcon icon={Alert02Icon} strokeWidth={2} className="size-4 text-destructive" />}
          <CardTitle className="text-sm font-semibold">{title}</CardTitle>
          <CardDescription className="ml-auto font-mono text-xs tabular-nums">
            {pct !== null && `${fmt(Math.round(pct))} %`}
            {elapsedMs !== undefined && ` · ${fmt(elapsedMs / 1000, 1)} s`}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 p-0">
          {pct !== null ? (
            <Progress value={pct} className={cn("h-1.5", status === "error" && "[&>div]:bg-destructive")} aria-label="Fortschritt" />
          ) : (
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted" role="progressbar" aria-label="Fortschritt (unbestimmt)">
              <div className="h-full w-1/3 animate-pulse rounded-full bg-foreground/40" />
            </div>
          )}
          {status === "running" && last && <Shimmer className="text-xs">{`${last.step}${last.detail ? ` · ${last.detail}` : ""}`}</Shimmer>}
          <ol className="flex flex-col gap-1">
            <AnimatePresence initial={false}>
              {steps.map((s, i) => (
                <motion.li
                  key={`${i}-${s.step}`}
                  initial={{ opacity: 0, x: -4 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-baseline gap-2 text-xs text-muted-foreground"
                >
                  {Number.isFinite(s.pct) && <span className="w-9 shrink-0 text-right font-mono tabular-nums">{fmt(Math.round(s.pct))} %</span>}
                  <span className={cn(i === steps.length - 1 && status === "running" && "text-foreground")}>{s.step}</span>
                  {s.detail && <span className="truncate">· {s.detail}</span>}
                </motion.li>
              ))}
            </AnimatePresence>
          </ol>
          {status === "error" && error && (
            <div role="alert" className="flex flex-col gap-2 rounded-xl border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {error}
              <FixLinks message={error} />
            </div>
          )}
          {children}
        </CardContent>
      </Card>
    </motion.div>
  );
}
