"use client";

import { useEffect, useState } from "react";
import { ApiError, apiPost } from "@/lib/api";
import type { StatQuery, StatResult } from "@/lib/types";

/** POST /api/statistik; 422 = deliberate abstention („nicht vorhanden …“), shown as such. */
export function useStat(query: StatQuery | null) {
  const key = query ? JSON.stringify(query) : null;
  const [state, setState] = useState<{ data?: StatResult; error?: ApiError; loading: boolean }>({ loading: !!key });
  useEffect(() => {
    if (!key) {
      setState({ loading: false });
      return;
    }
    const ctrl = new AbortController();
    setState((s) => ({ data: s.data, loading: true }));
    apiPost<StatResult>("/api/statistik", JSON.parse(key), ctrl.signal)
      .then((data) => setState({ data, loading: false }))
      .catch((e) => {
        if ((e as Error).name === "AbortError") return;
        setState({ error: e instanceof ApiError ? e : new ApiError(0, String(e)), loading: false });
      });
    return () => ctrl.abort();
  }, [key]);
  return state;
}

/** Pivot long rows [{monat, dim, wert}] into wide rows keyed by x with one column per series value. */
export function pivot(rows: StatResult["rows"], x: string, seriesDim: string): { data: Record<string, string | number | null>[]; series: { key: string; label: string }[] } {
  const seriesMap = new Map<string, string>();
  const byX = new Map<string, Record<string, string | number | null>>();
  for (const r of rows) {
    const sx = String(r[x]);
    const sv = String(r[seriesDim]);
    const key = `s_${sv.replace(/[^A-Za-z0-9_-]/g, "_")}`;
    seriesMap.set(key, String(r[`${seriesDim}_label`] ?? sv));
    const row = byX.get(sx) ?? { [x]: sx, [`${x}_label`]: String(r[`${x}_label`] ?? sx) };
    row[key] = r.wert;
    byX.set(sx, row);
  }
  return { data: [...byX.values()], series: [...seriesMap].map(([key, label]) => ({ key, label })) };
}
