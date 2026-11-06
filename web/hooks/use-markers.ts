"use client";

import { useMemo } from "react";
import type { Rule } from "@/lib/types";
import { useApi } from "./use-api";

export type Marker = { x: string; label: string; tone?: "warning" | "info"; rule: string; status: string };

/** Delivery-specific problem months, derived from the rule register (parameters.deliveries) – never hard-coded. */
export function useDqMarkers(): Marker[] {
  const rules = useApi<{ rules: Rule[] }>("/api/regeln");
  return useMemo(() => {
    const out: Marker[] = [];
    for (const r of rules.data?.rules ?? []) {
      const ds = (r.parameters as { deliveries?: string[] } | null)?.deliveries;
      if (!Array.isArray(ds)) continue;
      for (const d of ds)
        out.push({
          x: d,
          label: r.problem_id ?? r.rule_id,
          tone: r.status === "approved" ? "info" : "warning",
          rule: r.rule_id,
          status: r.status,
        });
    }
    return out;
  }, [rules.data]);
}
