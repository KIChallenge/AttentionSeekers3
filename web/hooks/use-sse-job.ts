"use client";

import { useCallback, useRef, useState } from "react";
import { ApiError, streamSse } from "@/lib/api";

export type ProgressStep = { step: string; pct: number; detail?: string | null };
export type JobState<R> = {
  status: "idle" | "running" | "done" | "error";
  steps: ProgressStep[];
  pct: number;
  result?: R;
  error?: string;
  startedAt?: number;
  finishedAt?: number;
};

/** Long-running backend job streamed as SSE (progress → result | error). */
export function useSseJob<R>() {
  const [state, setState] = useState<JobState<R>>({ status: "idle", steps: [], pct: 0 });
  const ctrl = useRef<AbortController | null>(null);

  const start = useCallback(async (path: string, body?: unknown): Promise<R | undefined> => {
    ctrl.current?.abort();
    const c = new AbortController();
    ctrl.current = c;
    setState({ status: "running", steps: [], pct: 0, startedAt: Date.now() });
    let result: R | undefined;
    let failed: string | undefined;
    try {
      await streamSse(
        path,
        body,
        ({ event, data }) => {
          if (event === "progress") {
            const p = data as ProgressStep;
            setState((s) => {
              const steps = [...s.steps];
              if (steps.length && steps[steps.length - 1].step === p.step) steps[steps.length - 1] = p;
              else steps.push(p);
              return { ...s, steps, pct: typeof p.pct === "number" ? p.pct : s.pct };
            });
          } else if (event === "result") {
            result = data as R;
          } else if (event === "error") {
            failed = (data as { message?: string })?.message ?? "Unbekannter Fehler";
          }
        },
        c.signal,
      );
    } catch (e) {
      if ((e as Error).name === "AbortError") return undefined;
      failed = e instanceof ApiError ? e.message : String(e);
    }
    if (failed || result === undefined) {
      setState((s) => ({ ...s, status: "error", error: failed ?? "Die Verbindung zum Backend ist abgebrochen, bevor ein Ergebnis kam (z. B. Backend neu gestartet). Es wurde nichts gespeichert – einfach erneut starten.", finishedAt: Date.now() }));
      return undefined;
    }
    setState((s) => ({ ...s, status: "done", pct: 100, result, finishedAt: Date.now() }));
    return result;
  }, []);

  const reset = useCallback(() => {
    ctrl.current?.abort();
    setState({ status: "idle", steps: [], pct: 0 });
  }, []);

  return { ...state, start, reset };
}
