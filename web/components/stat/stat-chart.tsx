"use client";

import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ComposedChart, LabelList, Line, Pie, PieChart, ReferenceLine, Scatter, ScatterChart, XAxis, YAxis } from "recharts";
import { createContext, useContext, useRef, useState } from "react";
import { fmt } from "@/lib/format";
import { type ChartConfig, ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip } from "@/components/ui/chart";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export type ChartSpec = {
  /** dot = dot plot on a zoomed axis: small differences between groups stay visible (bars must start at 0) */
  kind: "line" | "bar" | "area" | "pyramid" | "hbar" | "donut" | "dot";
  x: string;
  /** dashed = reference series (e.g. official value next to a user-defined recalculation) */
  /** title = full name shown on hover (legend) and in the tooltip, e.g. label „SVA“, title „Sozialversicherungsanstalt …“ */
  series: { key: string; label: string; dashed?: boolean; title?: string }[];
  data: Record<string, string | number | null | (number | null)[]>[];
  /** model band: data[band.key] = [lower, upper] (labelled „Modell“) */
  band?: { key: string; label: string };
  /** data[flagKey] truthy → point drawn in warning colour */
  flagKey?: string;
  /** vertical markers, e.g. DQ-affected months */
  markers?: { x: string; label: string; tone?: "warning" | "info"; /** shown on hover over the marker */ note?: string }[];
  unit?: string;
  /** zoom the value axis to the data range (lines/dots only – never bars); a note says the axis does not start at 0 */
  zoom?: boolean;
};

/** Value range of the given series with some padding, rounded to readable steps; null when nothing to zoom. */
export function zoomDomain(data: ChartSpec["data"], keys: string[]): [number, number] | null {
  const vals = data.flatMap((d) => keys.map((k) => d[k])).filter((v): v is number => typeof v === "number");
  if (vals.length < 2) return null;
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  if (hi === lo) return null;
  const pad = (hi - lo) * 0.25;
  const step = 10 ** Math.max(0, Math.floor(Math.log10(hi - lo)) - 1);
  return [Math.max(0, Math.floor((lo - pad) / step) * step), Math.ceil((hi + pad) / step) * step];
}

/** Relative spread (max − min) / max of the series values – small values mean bars from 0 would hide the differences. */
export function relativeSpread(data: ChartSpec["data"], keys: string[]): number {
  const vals = data.flatMap((d) => keys.map((k) => d[k])).filter((v): v is number => typeof v === "number");
  if (vals.length < 2) return 1;
  const hi = Math.max(...vals.map(Math.abs));
  return hi ? (Math.max(...vals) - Math.min(...vals)) / hi : 1;
}

const PIE = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--gray-alpha-600)", "var(--info)", "var(--gray-alpha-400)"];
const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)", "var(--gray-alpha-700)", "var(--info)"];

function compact(v: number) {
  const a = Math.abs(v);
  if (a >= 1_000_000) return `${fmt(v / 1_000_000, 1)} Mio.`;
  if (a >= 10_000) return `${fmt(Math.round(v / 1000))} Tsd.`;
  return fmt(v);
}

function TooltipBox({
  active,
  payload,
  label,
  config,
  unit,
  pyramid,
}: {
  active?: boolean;
  payload?: { dataKey?: string | number; value?: number | number[]; color?: string }[];
  label?: string | number;
  config: ChartConfig;
  unit?: string;
  pyramid?: boolean;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="grid min-w-36 gap-1.5 rounded-lg border border-border bg-background px-2.5 py-1.5 text-xs shadow-xl">
      <div className="font-medium">{label}</div>
      {payload.map((p) => (
        <div key={String(p.dataKey)} className="flex items-center gap-2">
          <span className="size-2 shrink-0 rounded-[2px]" style={{ background: p.color }} />
          <span className="text-muted-foreground">{config[String(p.dataKey)]?.label ?? p.dataKey}</span>
          <span className="ml-auto font-mono font-medium tabular-nums">
            {p.value === null || p.value === undefined
              ? "–"
              : Array.isArray(p.value)
                ? `${fmt((p.value as number[])[0])} – ${fmt((p.value as number[])[1])}`
                : fmt(pyramid ? Math.abs(p.value) : p.value)}
            {unit === "%" ? " %" : ""}
          </span>
        </div>
      ))}
    </div>
  );
}

/** Chart motion (W-04): Recharts' own animations restart on every re-render and on the dashboard never finished (only dots
 * and axes visible). Recharts animations therefore stay off; the chart fades and rises in with CSS instead (tw-animate-css),
 * which cannot leave a chart half-drawn. `motion-reduce` disables it. */
const ANIM = { isAnimationActive: false } as const;
const ENTER = "animate-in fade-in-0 slide-in-from-bottom-1 duration-500 motion-reduce:animate-none";

/** Shows a marker's note immediately (HTML tooltip over the chart) – the SVG/browser title tooltip needed ~1 s. */
const MarkerTipCtx = createContext<(tip: { text: string; x: number; y: number } | null, e?: React.MouseEvent) => void>(() => {});

function MarkerLabel({ viewBox, text, note, color }: { viewBox?: { x?: number; y?: number }; text: string; note?: string; color: string }) {
  const show = useContext(MarkerTipCtx);
  const x = (viewBox?.x ?? 0) + 4;
  const y = (viewBox?.y ?? 0) + 12;
  return (
    <g
      style={{ cursor: note ? "default" : undefined }}
      onMouseEnter={note ? (e) => show({ text: note, x: 0, y: 0 }, e) : undefined}
      onMouseMove={note ? (e) => show({ text: note, x: 0, y: 0 }, e) : undefined}
      onMouseLeave={note ? () => show(null) : undefined}
    >
      {note && <rect x={x - 8} y={y - 12} width={text.length * 6 + 26} height={18} fill="transparent" />}
      <text x={x} y={y} fontSize={10} fill={color}>
        {text}
        {note ? " ⓘ" : ""}
      </text>
    </g>
  );
}

export function StatChart(props: { spec: ChartSpec; height?: number }) {
  const wrap = useRef<HTMLDivElement>(null);
  const [tip, setTip] = useState<{ text: string; x: number; y: number } | null>(null);
  const show = (t: { text: string; x: number; y: number } | null, e?: React.MouseEvent) => {
    if (!t || !e || !wrap.current) return setTip(null);
    const r = wrap.current.getBoundingClientRect();
    setTip({ text: t.text, x: e.clientX - r.left, y: e.clientY - r.top });
  };
  return (
    <MarkerTipCtx.Provider value={show}>
      <div ref={wrap} className="relative">
        <StatChartBody {...props} />
        {tip && (
          <div
            role="tooltip"
            className="pointer-events-none absolute z-20 max-w-xs -translate-x-1/2 -translate-y-full rounded-md bg-foreground px-2.5 py-1.5 text-xs text-background shadow-md"
            style={{ left: tip.x, top: tip.y - 10 }}
          >
            {tip.text}
          </div>
        )}
      </div>
    </MarkerTipCtx.Provider>
  );
}

/** Legend with short codes; the full name appears immediately on hover – instead of listing all names in the description. */
function TitledLegend({ payload, series }: { payload?: { dataKey?: string | number; color?: string }[]; series: ChartSpec["series"] }) {
  const byKey = new Map(series.map((s) => [s.key, s]));
  return (
    <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 pt-3 text-xs">
      {(payload ?? []).map((p) => {
        const s = byKey.get(String(p.dataKey));
        if (!s) return null;
        const item = (
          <span className="flex items-center gap-1.5">
            <span className="size-2 shrink-0 rounded-[2px]" style={{ background: p.color }} />
            <span className={s.title ? "underline decoration-dotted underline-offset-4" : undefined}>{s.label}</span>
          </span>
        );
        if (!s.title) return <span key={s.key}>{item}</span>;
        // app tooltip without delay (the browser's title tooltip needs ~1 s and shows a „?“ cursor)
        return (
          <Tooltip key={s.key} delayDuration={0}>
            <TooltipTrigger asChild>
              <span tabIndex={0} className="outline-none">
                {item}
              </span>
            </TooltipTrigger>
            <TooltipContent>{s.title}</TooltipContent>
          </Tooltip>
        );
      })}
    </div>
  );
}

function StatChartBody({ spec, height = 260 }: { spec: ChartSpec; height?: number }) {
  const anim = ANIM;
  const config: ChartConfig = Object.fromEntries(
    spec.series.map((s, i) => [s.key, { label: s.title ? `${s.label} – ${s.title}` : s.label, color: COLORS[i % COLORS.length] }]),
  );
  const titled = spec.series.some((s) => s.title);
  const legend = titled ? <ChartLegend content={<TitledLegend series={spec.series} />} /> : <ChartLegend content={<ChartLegendContent />} />;
  if (spec.band) config[spec.band.key] = { label: spec.band.label, color: "var(--gray-alpha-400)" };
  const multi = spec.series.length > 1;
  const markers = (spec.markers ?? []).filter((m) => spec.data.some((d) => d[spec.x] === m.x));
  const markerEls = markers.map((m) => {
    const color = m.tone === "info" ? "var(--info)" : "var(--warning)";
    return (
      <ReferenceLine
        key={m.x}
        x={m.x}
        stroke={color}
        strokeDasharray="3 3"
        label={<MarkerLabel text={m.label} note={m.note} color={color} />}
      />
    );
  });
  const zoom = spec.zoom && (spec.kind === "line" || spec.kind === "area" || spec.kind === "dot") ? zoomDomain(spec.data, spec.series.map((s) => s.key)) : null;
  const zoomNote = zoom ? (
    <p className="mt-1 text-[11px] text-muted-foreground">
      Achse gezoomt: beginnt bei {compact(zoom[0])}, nicht bei 0 – die Unterschiede sind vergrößert dargestellt.
    </p>
  ) : null;
  const common = (zero: boolean) => (
    <>
      <CartesianGrid vertical={false} strokeDasharray="3 3" />
      <XAxis dataKey={spec.x} tickLine={false} axisLine={false} tickMargin={8} minTickGap={16} fontSize={11} />
      <YAxis tickLine={false} axisLine={false} width={64} fontSize={11} tickFormatter={(v: number) => compact(v)} domain={zoom ?? (zero ? [0, "auto"] : ["auto", "auto"])} allowDataOverflow={!!zoom} />
      <ChartTooltip cursor={{ fill: "var(--gray-alpha-100)" }} content={<TooltipBox config={config} unit={spec.unit} />} />
      {multi && legend}
    </>
  );
  if (spec.kind === "dot") {
    const key = spec.series[0]?.key;
    const rows = spec.data.filter((d) => typeof d[key] === "number");
    const dom = zoomDomain(rows, [key]) ?? ["auto", "auto"];
    const h = Math.max(height, rows.length * 26 + 50);
    return (
      <div className={ENTER}>
        <ChartContainer config={config} className="w-full" style={{ height: h }}>
          <ScatterChart margin={{ left: 8, right: 56, top: 8, bottom: 4 }}>
            <CartesianGrid horizontal={false} strokeDasharray="3 3" />
            <XAxis type="number" dataKey={key} domain={dom} allowDataOverflow tickLine={false} axisLine={false} fontSize={11} tickFormatter={(v: number) => compact(v)} />
            <YAxis type="category" dataKey={spec.x} allowDuplicatedCategory={false} tickLine={false} axisLine={false} width={150} fontSize={11} interval={0} />
            <ChartTooltip cursor={{ strokeDasharray: "3 3" }} content={<TooltipBox config={config} unit={spec.unit} />} />
            <Scatter data={rows} fill={`var(--color-${key})`} {...anim}>
              <LabelList dataKey={key} position="right" fontSize={10} formatter={(v: unknown) => {
                  const n = Number(v);
                  const dec = !Number.isInteger(n) && Math.abs(n) < 100 ? 2 : 0;   // rates like 5,57 keep their decimals
                  return `${fmt(n, dec)}${spec.unit === "%" ? " %" : ""}`;
                }} />
            </Scatter>
          </ScatterChart>
        </ChartContainer>
        {dom[0] !== "auto" && (
          <p className="mt-1 text-[11px] text-muted-foreground">
            Punktdiagramm mit gezoomter Achse ({compact(dom[0] as number)} – {compact(dom[1] as number)}): die Unterschiede sind klein und wären in Balken ab 0 kaum zu sehen.
          </p>
        )}
      </div>
    );
  }
  if (spec.kind === "donut") {
    const key = spec.series[0]?.key;
    const rows = spec.data.filter((d) => typeof d[key] === "number" && (d[key] as number) > 0);
    const pieConfig: ChartConfig = Object.fromEntries(rows.map((d, i) => [String(d[spec.x]), { label: String(d[spec.x]), color: PIE[i % PIE.length] }]));
    return (
      <div className={`${ENTER} grid items-center gap-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]`}>
        <ChartContainer config={pieConfig} className="mx-auto aspect-square w-full max-w-[260px]">
          <PieChart>
            <ChartTooltip content={<TooltipBox config={{ [key]: { label: spec.series[0].label } }} unit={spec.unit} />} />
            <Pie data={rows} dataKey={key} nameKey={spec.x} innerRadius="55%" outerRadius="90%" strokeWidth={2} {...anim}>
              {rows.map((d, i) => (
                <Cell key={String(d[spec.x])} fill={PIE[i % PIE.length]} stroke="var(--background)" />
              ))}
            </Pie>
          </PieChart>
        </ChartContainer>
        <ul className="flex flex-col gap-1 text-xs">
          {rows.map((d, i) => (
            <li key={String(d[spec.x])} className="flex items-center gap-2">
              <span className="size-2.5 shrink-0 rounded-[3px]" style={{ background: PIE[i % PIE.length] }} />
              <span className="min-w-0 flex-1 truncate">{String(d[spec.x])}</span>
              <span className="font-mono tabular-nums">{fmt(d[key] as number)}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }
  if (spec.kind === "pyramid" || spec.kind === "hbar") {
    const pyramid = spec.kind === "pyramid";
    const data = pyramid
      ? spec.data.map((d) => ({ ...d, [spec.series[0].key]: -Math.abs(Number(d[spec.series[0].key] ?? 0)) }))
      : spec.data;
    const h = Math.max(height, data.length * 22 + 40);
    return (
      <ChartContainer config={config} className={`${ENTER} w-full`} style={{ height: h }}>
        <BarChart data={data} layout="vertical" stackOffset={pyramid ? "sign" : undefined} margin={{ left: 8, right: 16 }} barCategoryGap={2}>
          <CartesianGrid horizontal={false} strokeDasharray="3 3" />
          <XAxis type="number" tickLine={false} axisLine={false} fontSize={11} tickFormatter={(v: number) => compact(Math.abs(v))} />
          <YAxis type="category" dataKey={spec.x} tickLine={false} axisLine={false} width={pyramid ? 56 : 150} fontSize={11} interval={0} />
          <ChartTooltip cursor={{ fill: "var(--gray-alpha-100)" }} content={<TooltipBox config={config} unit={spec.unit} pyramid={pyramid} />} />
          {multi && legend}
          {spec.series.map((s) => (
            <Bar key={s.key} dataKey={s.key} stackId={pyramid ? "p" : undefined} fill={`var(--color-${s.key})`} fillOpacity={s.dashed ? 0.3 : 1} radius={pyramid ? 2 : 4} {...anim} />
          ))}
        </BarChart>
      </ChartContainer>
    );
  }
  if (spec.kind === "bar")
    return (
      <ChartContainer config={config} className={`${ENTER} w-full`} style={{ height }}>
        <BarChart data={spec.data} margin={{ left: 0, right: 8, top: 16 }}>
          {common(true)}
          {markerEls}
          {spec.series.map((s) => (
            <Bar key={s.key} dataKey={s.key} fill={`var(--color-${s.key})`} fillOpacity={s.dashed ? 0.3 : 1} radius={4} {...anim} />
          ))}
        </BarChart>
      </ChartContainer>
    );
  if (spec.kind === "area")
    return (
      <ChartContainer config={config} className={`${ENTER} w-full`} style={{ height }}>
        <AreaChart data={spec.data} margin={{ left: 0, right: 8, top: 16 }}>
          {common(true)}
          {markerEls}
          {spec.series.map((s) => (
            <Area key={s.key} dataKey={s.key} type="monotone" stroke={`var(--color-${s.key})`} fill={`var(--color-${s.key})`} fillOpacity={0.12} strokeWidth={2} {...anim} />
          ))}
        </AreaChart>
      </ChartContainer>
    );
  return (
    <>
    <ChartContainer config={config} className={`${ENTER} w-full`} style={{ height }}>
      <ComposedChart data={spec.data} margin={{ left: 0, right: 8, top: 16 }}>
        {common(false)}
        {markerEls}
        {spec.band && (
          <Area dataKey={spec.band.key} type="monotone" stroke="none" fill="var(--gray-alpha-300)" fillOpacity={0.6} {...anim} connectNulls={false} />
        )}
        {spec.series.map((s) => (
          <Line
            key={s.key}
            dataKey={s.key}
            type="monotone"
            stroke={`var(--color-${s.key})`}
            strokeWidth={s.dashed ? 1.5 : 2}
            strokeDasharray={s.dashed ? "5 4" : undefined}
            strokeOpacity={s.dashed ? 0.6 : 1}
            dot={
              spec.flagKey
                ? (props: { cx?: number; cy?: number; payload?: Record<string, unknown>; index?: number }) => {
                    const flagged = !!props.payload?.[spec.flagKey as string];
                    if (props.cx === undefined || props.cy === undefined) return <g key={props.index} />;
                    return (
                      <circle
                        key={props.index}
                        cx={props.cx}
                        cy={props.cy}
                        r={flagged ? 4.5 : 2.5}
                        fill={flagged ? "var(--warning)" : "var(--background)"}
                        stroke={flagged ? "var(--warning)" : `var(--color-${s.key})`}
                        strokeWidth={1.5}
                      />
                    );
                  }
                : { r: 2.5 }
            }
            activeDot={{ r: 4 }}
            connectNulls={false}
            {...anim}
          />
        ))}
      </ComposedChart>
    </ChartContainer>
    {zoomNote}
    </>
  );
}
