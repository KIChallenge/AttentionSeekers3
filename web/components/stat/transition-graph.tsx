"use client";

import { Background, Controls, type Edge, MarkerType, type Node, Position, ReactFlow, type ReactFlowInstance } from "@xyflow/react";
import { useMemo, useState } from "react";
import { fmt } from "@/lib/format";
import type { KlassExplanation } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Switch } from "./switch";

const COL_GAP = 300; // room for the edges and their labels between two versions
const ROW_GAP = 64;
const NODE_W = 200;

/**
 * Transition graph (klass_uebergang) – one column per version, old left, new right.
 * By default only the transitions that touch the selected code are drawn (the API returns the whole neighbourhood,
 * which becomes unreadable); a switch shows all.
 */
export function TransitionGraph({
  explanation,
  focus,
  onPick,
  height,
}: {
  explanation: KlassExplanation;
  focus?: string;
  onPick?: (code: string, version: string) => void;
  height?: number;
}) {
  const [showAll, setShowAll] = useState(false);
  const focusCode = focus?.split("|").pop();
  const focusId = useMemo(() => {
    if (!focus) return undefined;
    if (explanation.nodes.some((n) => n.id === focus)) return focus;
    // version unknown („-“) → pick the node with this code that has the most edges
    const cands = explanation.nodes.filter((n) => n.code === focusCode);
    const deg = (id: string) => explanation.edges.filter((e) => `${e.version_alt}|${e.code_alt}` === id || `${e.version_neu}|${e.code_neu}` === id).length;
    return cands.sort((a, b) => deg(b.id) - deg(a.id))[0]?.id;
  }, [explanation, focus, focusCode]);

  const touching = useMemo(
    () => explanation.edges.filter((e) => focusId && (`${e.version_alt}|${e.code_alt}` === focusId || `${e.version_neu}|${e.code_neu}` === focusId)),
    [explanation.edges, focusId],
  );
  const reduced = !!focusId && touching.length > 0 && touching.length < explanation.edges.length;
  const edgesShown = reduced && !showAll ? touching : explanation.edges;

  const { nodes, edges, rows } = useMemo(() => {
    const ids = new Set(edgesShown.flatMap((e) => [`${e.version_alt}|${e.code_alt}`, `${e.version_neu}|${e.code_neu}`]));
    if (focusId) ids.add(focusId);
    const shown = explanation.nodes.filter((n) => ids.has(n.id));
    const versions = [...new Set(shown.map((n) => n.version))].sort();
    // order rows by share of the edge to/from the focus (largest first), focus column first
    const weight = (id: string) =>
      Math.max(
        0,
        ...edgesShown
          .filter((e) => `${e.version_alt}|${e.code_alt}` === id || `${e.version_neu}|${e.code_neu}` === id)
          .map((e) => e.anteil ?? 0),
      );
    const byCol = new Map<string, typeof shown>();
    for (const v of versions) byCol.set(v, shown.filter((n) => n.version === v).sort((a, b) => weight(b.id) - weight(a.id) || a.code.localeCompare(b.code)));
    const rows = Math.max(1, ...[...byCol.values()].map((c) => c.length));
    const nodes: Node[] = [];
    for (const [v, col] of byCol) {
      const x = versions.indexOf(v) * COL_GAP;
      col.forEach((n, i) => {
        const isFocus = n.id === focusId;
        nodes.push({
          id: n.id,
          position: { x, y: (i - (col.length - 1) / 2) * ROW_GAP },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          data: {
            label: (
              <div className="flex flex-col gap-0.5 text-left" title={`${n.code} ${n.label} (${n.version})`}>
                <span className="font-mono text-[10px] text-muted-foreground">{n.version}</span>
                <span className="flex min-w-0 gap-1 text-xs">
                  <span className="shrink-0 font-mono font-medium">{n.code}</span>
                  <span className="truncate">{n.label}</span>
                </span>
              </div>
            ),
          },
          style: {
            width: NODE_W,
            borderRadius: 10,
            padding: "6px 10px",
            fontSize: 12,
            borderColor: isFocus ? "var(--foreground)" : undefined,
            borderWidth: isFocus ? 2 : 1,
            boxShadow: "none",
          },
        });
      });
    }
    const labelled = edgesShown.length <= 16;
    const edges: Edge[] = edgesShown.map((e, i) => {
      const touchesFocus = `${e.version_alt}|${e.code_alt}` === focusId || `${e.version_neu}|${e.code_neu}` === focusId;
      return {
        id: `e${i}`,
        source: `${e.version_alt}|${e.code_alt}`,
        target: `${e.version_neu}|${e.code_neu}`,
        label: labelled ? `${e.beziehung}${e.anteil !== null && e.anteil !== undefined ? ` · ${fmt(Math.round(e.anteil * 100))} %` : ""}` : undefined,
        labelStyle: { fontSize: 10, fill: "var(--muted-foreground)" },
        labelBgStyle: { fill: "var(--background)" },
        labelBgPadding: [4, 2] as [number, number],
        markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
        style: { strokeWidth: touchesFocus ? 1.6 : 1, opacity: touchesFocus || !focusId ? 1 : 0.45 },
      };
    });
    return { nodes, edges, rows };
  }, [edgesShown, explanation.nodes, focusId]);

  const h = height ?? Math.min(560, Math.max(220, rows * ROW_GAP + 80));
  const refit = (rf: ReactFlowInstance) => setTimeout(() => rf.fitView({ padding: 0.12, maxZoom: 1.1 }), 60);

  return (
    <div className="flex flex-col gap-2">
      {reduced && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <Switch checked={showAll} onChange={setShowAll} label={`alle ${explanation.edges.length} Übergänge der Nachbarschaft zeigen`} />
          {!showAll && <span>gezeigt: {touching.length} Übergänge des gewählten Codes</span>}
        </div>
      )}
      <div className={cn("overflow-hidden rounded-xl border border-border")} style={{ height: h }} aria-label="Übergangsgraph">
        <ReactFlow
          key={`${focusId}-${showAll}`}
          nodes={nodes}
          edges={edges}
          fitView
          fitViewOptions={{ padding: 0.12, maxZoom: 1.1 }}
          onInit={refit}
          minZoom={0.2}
          nodesDraggable={false}
          nodesConnectable={false}
          proOptions={{ hideAttribution: true }}
          onNodeClick={(_, n) => {
            const [v, ...c] = n.id.split("|");
            onPick?.(c.join("|"), v);
          }}
        >
          <Background gap={16} size={1} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
    </div>
  );
}
