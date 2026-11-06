"use client";

import { DatabaseIcon, File02Icon, FileSecurityIcon, Layers01Icon, PlayCircleIcon, UserCheck01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import Link from "next/link";
import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { ApiError, apiPost } from "@/lib/api";
import { fmtDateTime, fmtMonth, shortHash, ruleSetLabel } from "@/lib/format";
import type { Evidence, ExampleRecords } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { CopyButton, SqlBlock } from "./code-block";
import { ErrorState, LoadingState } from "./states";

export type EvidenceRequest = {
  title: string;
  /** formatted value exactly as returned by the API */
  value?: string;
  definition?: string;
  evidence?: Evidence | null;
  sql?: string | null;
  extraSql?: { title: string; sql: string }[];
  /** example records behind the number (POST /api/quellennachweis) */
  examples?: { regelwerk: string; monat: string; filter?: Record<string, string | string[]>; vvhIds?: string[] } | null;
  warnings?: string[];
  note?: string;
  initialTab?: "nachweis" | "sql" | "saetze";
};

const Ctx = createContext<(req: EvidenceRequest) => void>(() => {});
export const useEvidence = () => useContext(Ctx);
/** closes the panel when one of its links navigates away */
const CloseCtx = createContext<() => void>(() => {});

/** Link inside the evidence panel: navigates and closes the panel. */
function EvLink({ href, children, className, title }: { href: string; children: ReactNode; className?: string; title?: string }) {
  const close = useContext(CloseCtx);
  return (
    <Link href={href} onClick={close} title={title} className={cn("underline decoration-dotted underline-offset-4 hover:decoration-solid", className)}>
      {children}
    </Link>
  );
}

export function EvidenceProvider({ children }: { children: ReactNode }) {
  const [req, setReq] = useState<EvidenceRequest | null>(null);
  const [open, setOpen] = useState(false);
  const show = useCallback((r: EvidenceRequest) => {
    setReq(r);
    setOpen(true);
  }, []);
  return (
    <Ctx.Provider value={show}>
      {children}
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="right" className="w-full gap-0 overflow-y-auto p-0 sm:max-w-2xl">
          <CloseCtx.Provider value={() => setOpen(false)}>{req && <EvidenceBody key={JSON.stringify(req).slice(0, 400)} req={req} />}</CloseCtx.Provider>
        </SheetContent>
      </Sheet>
    </Ctx.Provider>
  );
}

function EvidenceBody({ req }: { req: EvidenceRequest }) {
  const [examples, setExamples] = useState<ExampleRecords | null>(null);
  const [exEvidence, setExEvidence] = useState<Evidence | null>(null);
  const [exError, setExError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);
  const ex = req.examples;
  useEffect(() => {
    if (!ex) return;
    const ctrl = new AbortController();
    setLoading(true);
    apiPost<{ evidence: Evidence; examples: ExampleRecords }>(
      "/api/quellennachweis",
      {
        regelwerk: ex.regelwerk,
        monat: ex.monat,
        filter: ex.filter ?? {},
        limit: ex.vvhIds?.length ? Math.min(20, Math.max(ex.vvhIds.length, 5)) : 8,
        ...(ex.vvhIds?.length ? { vvh_ids: ex.vvhIds.slice(0, 20) } : {}),
      },
      ctrl.signal,
    )
      .then((r) => {
        setExamples(r.examples);
        setExEvidence(r.evidence);
      })
      .catch((e) => {
        if ((e as Error).name !== "AbortError") setExError(e instanceof ApiError ? e : new ApiError(0, String(e)));
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [ex]);
  const evidence = req.evidence ?? exEvidence;
  return (
    <>
      <SheetHeader className="gap-1 border-b border-border p-5 pr-12 text-left">
        <SheetDescription className="text-xs font-medium">Quellennachweis</SheetDescription>
        <SheetTitle className="text-lg">{req.title}</SheetTitle>
        {req.value && <p className="text-3xl font-medium tabular-nums">{req.value}</p>}
        {req.definition && <p className="text-xs text-muted-foreground">{req.definition}</p>}
        {req.warnings?.map((w) => (
          <p key={w} className="text-xs text-warning">
            {w}
          </p>
        ))}
      </SheetHeader>
      <Tabs defaultValue={req.initialTab ?? (ex?.vvhIds?.length ? "saetze" : "nachweis")} className="gap-4 p-5">
        <TabsList className="bg-muted">
          <TabsTrigger value="nachweis">Nachweis</TabsTrigger>
          <TabsTrigger value="sql" disabled={!req.sql && !examples && !req.extraSql?.length}>
            SQL
          </TabsTrigger>
          <TabsTrigger value="saetze" disabled={!ex}>
            Beispielsätze
          </TabsTrigger>
        </TabsList>
        <TabsContent value="nachweis" className="flex flex-col gap-5">
          {req.note && <p className="text-sm text-muted-foreground">{req.note}</p>}
          {evidence ? <EvidenceDetails evidence={evidence} /> : loading ? <LoadingState rows={2} /> : <p className="text-sm text-muted-foreground">Kein strukturierter Nachweis übergeben.</p>}
        </TabsContent>
        <TabsContent value="sql" className="flex flex-col gap-3">
          {req.sql && <SqlBlock code={req.sql} title="Abfrage der Zahl" />}
          {req.extraSql?.map((s) => (
            <SqlBlock key={s.title} code={s.sql} title={s.title} />
          ))}
          {examples && <SqlBlock code={examples.sql_read} title="Beispielsätze – wie gelesen" />}
          {examples && <SqlBlock code={examples.sql_delivered} title="Beispielsätze – wie geliefert (roh.lieferung)" />}
        </TabsContent>
        <TabsContent value="saetze">
          {loading && <LoadingState label="Beispielsätze werden abgefragt …" />}
          {exError && <ErrorState error={exError} what="Beispielsätze" />}
          {examples && ex && <ExampleRecordsView examples={examples} vvhIds={ex.vvhIds} />}
        </TabsContent>
      </Tabs>
    </>
  );
}

function Row({ icon, label, children }: { icon: typeof File02Icon; label: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        <HugeiconsIcon icon={icon} strokeWidth={2} className="size-3.5" />
        {label}
      </h3>
      <div className="flex flex-col gap-1.5">{children}</div>
    </section>
  );
}

function Line({ children }: { children: ReactNode }) {
  return <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-border px-3 py-2 text-sm">{children}</div>;
}

export function EvidenceDetails({ evidence }: { evidence: Evidence }) {
  return (
    <div className="flex flex-col gap-5">
      <Row icon={File02Icon} label="Lieferungen (unverändert, SHA-256)">
        {evidence.deliveries.length === 0 && <span className="text-sm text-muted-foreground">keine</span>}
        {evidence.deliveries.map((d) => (
          <Line key={d.month + d.file}>
            <EvLink href={`/lieferungen?monat=${d.month}`} className="font-medium" title="Lieferung in der Problemmatrix öffnen">
              {fmtMonth(d.month)}
            </EvLink>
            <EvLink href={`/lieferungen?ansicht=dateien&q=${encodeURIComponent(d.file)}`} className="font-mono text-xs text-muted-foreground" title="Im Dateiregister öffnen">
              {d.file}
            </EvLink>
            <span className="ml-auto flex items-center gap-1 font-mono text-xs" title={d.sha256}>
              {shortHash(d.sha256, 16)}
              <CopyButton text={d.sha256} label="SHA-256 kopieren" />
            </span>
          </Line>
        ))}
      </Row>
      <Row icon={PlayCircleIcon} label="Läufe (Prüfsumme)">
        {evidence.runs.length === 0 && <span className="text-sm text-muted-foreground">keine</span>}
        {evidence.runs.map((r) => (
          <Line key={r.run_id}>
            <EvLink href={`/laeufe?lauf=${r.run_id}`} className="font-medium" title="Lauf mit Kennzahlen und Auffälligkeiten öffnen">
              Lauf {r.run_id}
            </EvLink>
            <span className="text-muted-foreground">{fmtMonth(r.month)}</span>
            <Badge variant="secondary">{r.status === "vorlaeufig" ? "vorläufig" : r.status === "veroeffentlicht" ? "veröffentlicht" : r.status}</Badge>
            {r.finished_at && <span className="text-xs text-muted-foreground">{fmtDateTime(r.finished_at)}</span>}
            <span className="ml-auto flex items-center gap-1 font-mono text-xs" title={r.checksum}>
              {r.checksum}
              <CopyButton text={r.checksum} label="Prüfsumme kopieren" />
            </span>
          </Line>
        ))}
      </Row>
      <Row icon={UserCheck01Icon} label={`Angewendete Regeln · Regelwerk „${ruleSetLabel(evidence.rule_set)}“`}>
        {evidence.rules.length === 0 && <span className="text-sm text-muted-foreground">keine Leseregeln angewendet</span>}
        {evidence.rules.map((r) => (
          <Line key={r.id}>
            <EvLink href={`/freigaben?regel=${r.id}`} className="font-mono text-xs font-medium" title="Regel in Freigaben öffnen">
              {r.id}
            </EvLink>
            <span className="min-w-0 flex-1">{r.title}</span>
            <span className="w-full text-xs text-muted-foreground">
              {r.approved_by ? `freigegeben von ${r.approved_by} · ${fmtDateTime(r.approved_at)}` : "nicht freigegeben"}
              {r.problem ? ` · ${r.problem}` : ""}
            </span>
          </Line>
        ))}
      </Row>
      <Row icon={Layers01Icon} label="Klassifikation">
        <Line>
          <span>{evidence.klass_versions.length ? evidence.klass_versions.join(", ") : "–"}</span>
          {evidence.klass_run && (
            <span className="ml-auto font-mono text-xs text-muted-foreground" title={evidence.klass_run.checksum}>
              <EvLink href="/klassifikationen">Lauf {evidence.klass_run.run_id}</EvLink> · {shortHash(evidence.klass_run.checksum, 16)}
            </span>
          )}
        </Line>
      </Row>
    </div>
  );
}

const READ_COLS: [string, string][] = [
  ["vvh_id", "VVH"],
  ["person_id", "Person"],
  ["begin_date", "Beginn"],
  ["end_date", "Ende"],
  ["region", "Bundesland"],
  ["oenace", "ÖNACE"],
  ["geschlecht", "Geschl."],
  ["qualifikation", "Qualifikation"],
  ["alter", "Alter"],
  ["origin", "Herkunft"],
];
const RAW_COLS: [string, string][] = [
  ["vvh_id", "VVH_ID"],
  ["person_id", "PERSON_ID"],
  ["beginn", "BEGINN"],
  ["ende", "ENDE"],
  ["bundesland", "BUNDESLAND"],
  ["oenace", "OENACE"],
  ["geschlecht", "GESCHLECHT"],
  ["qual", "QUAL"],
  ["geburtsdatum", "GEBURTSDATUM"],
];

function cell(v: unknown) {
  if (v === null || v === undefined || v === "") return <span className="text-muted-foreground/70">leer</span>;
  if (Array.isArray(v)) return v.join(", ");
  return String(v);
}

export function ExampleRecordsView({ examples, vvhIds }: { examples: ExampleRecords; vvhIds?: string[] }) {
  const [mode, setMode] = useState<"geliefert" | "gelesen">("geliefert");
  const read = examples.read;
  const delivered = examples.delivered;
  const rows = mode === "geliefert" ? delivered : read;
  const cols = mode === "geliefert" ? RAW_COLS : READ_COLS;
  const notCounted = vvhIds?.length ? vvhIds.filter((id) => !read.some((r) => String(r.vvh_id) === id)) : [];
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <ToggleGroup
          type="single"
          value={mode}
          onValueChange={(v) => v && setMode(v as "geliefert" | "gelesen")}
          size="sm"
          variant="outline"
          aria-label="Darstellung der Beispielsätze"
        >
          <ToggleGroupItem value="geliefert" className="px-3">
            wie geliefert
          </ToggleGroupItem>
          <ToggleGroupItem value="gelesen" className="px-3">
            wie gelesen
          </ToggleGroupItem>
        </ToggleGroup>
        <span className="text-xs text-muted-foreground">
          {mode === "geliefert" ? "roh.lieferung – Originalwerte, nie verändert" : "store.month_record – nach freigegebenen Leseregeln"}
        </span>
      </div>
      {mode === "gelesen" && notCounted.length > 0 && (
        <p className="rounded-xl border border-border bg-muted px-3 py-2 text-xs text-muted-foreground">
          VVH {notCounted.join(", ")}: in diesem Monat nicht gezählt (kein Abschnitt am Stichtag) – daher kein Satz „wie gelesen“. Die gelieferten Sätze
          stehen unter „wie geliefert“.
        </p>
      )}
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">Keine Sätze.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                {cols.map(([k, l]) => (
                  <TableHead key={k} className={cn("h-8 text-xs", mode === "geliefert" && "font-mono")}>
                    {l}
                  </TableHead>
                ))}
                {mode === "gelesen" && <TableHead className="h-8 text-xs">Probleme / Regeln</TableHead>}
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r, i) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: rows have no unique key (several segments per VVH)
                <TableRow key={i}>
                  {cols.map(([k]) => (
                    <TableCell key={k} className="py-1.5 font-mono text-xs whitespace-nowrap">
                      {cell(r[k])}
                    </TableCell>
                  ))}
                  {mode === "gelesen" && (
                    <TableCell className="py-1.5">
                      <div className="flex flex-wrap gap-1">
                        {((r.problems as string[]) ?? []).map((p) => (
                          <Badge key={p} className="bg-warning/10 text-warning">
                            {p}
                          </Badge>
                        ))}
                        {((r.rules as string[]) ?? []).map((p) => (
                          <Badge key={p} variant="secondary">
                            {p}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

/** Chips under a number: „Lieferung 2025-06 · Lauf 33 · R-DQ01, R-DQ07“ → open Quellennachweis. */
export function EvidenceChips({ req, className }: { req: EvidenceRequest; className?: string }) {
  const open = useEvidence();
  const ev = req.evidence;
  const parts: { key: string; icon: typeof File02Icon; label: string; tab: EvidenceRequest["initialTab"] }[] = [];
  if (ev) {
    if (ev.deliveries.length)
      parts.push({
        key: "l",
        icon: File02Icon,
        label: ev.deliveries.length === 1 ? `Lieferung ${ev.deliveries[0].month}` : `${ev.deliveries.length} Lieferungen`,
        tab: "nachweis",
      });
    if (ev.runs.length)
      parts.push({ key: "r", icon: PlayCircleIcon, label: ev.runs.length === 1 ? `Lauf ${ev.runs[0].run_id}` : `${ev.runs.length} Läufe`, tab: "nachweis" });
    if (ev.rules.length) parts.push({ key: "g", icon: UserCheck01Icon, label: ev.rules.map((r) => r.id).join(", "), tab: "nachweis" });
  }
  if (req.sql) parts.push({ key: "s", icon: DatabaseIcon, label: "SQL", tab: "sql" });
  if (req.examples) parts.push({ key: "e", icon: FileSecurityIcon, label: "Sätze", tab: "saetze" });
  if (!parts.length) parts.push({ key: "n", icon: FileSecurityIcon, label: "Quellennachweis", tab: "nachweis" });
  return (
    <div className={cn("flex flex-wrap items-center gap-1.5", className)}>
      {parts.map((p) => (
        <Button
          key={p.key}
          type="button"
          variant="outline"
          size="xs"
          className="h-5 gap-1 rounded-full px-2 text-xs font-medium tabular-nums [&_svg]:size-3"
          aria-label={`Quellennachweis öffnen: ${p.label}`}
          onClick={() => open({ ...req, initialTab: p.tab })}
        >
          <HugeiconsIcon icon={p.icon} strokeWidth={2} aria-hidden="true" />
          {p.label}
        </Button>
      ))}
    </div>
  );
}
