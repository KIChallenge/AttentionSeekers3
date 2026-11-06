"use client";

import { ArrowUp02Icon, StopIcon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import Link from "next/link";
import { AnimatePresence, motion } from "motion/react";
import { useRef, useState } from "react";
import { Streamdown } from "streamdown";
import { useApi } from "@/hooks/use-api";
import { ApiError, streamSse } from "@/lib/api";
import { fmt, fmtDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useUser } from "@/components/shell/user-provider";
import { Switch } from "@/components/stat/switch";
import { StatusBadge } from "@/components/stat/badges";
import { CodeBlock, SqlBlock } from "@/components/stat/code-block";
import { PageHeading, PageShell, Panel, SectionTitle } from "@/components/stat/page-shell";
import { Shimmer } from "@/components/stat/shimmer";
import { EmptyState, ErrorState, LoadingState } from "@/components/stat/states";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type BeforeAfter = { label: string; before: number | null; after: number | null };
type Proposal = {
  kind: "rule" | "code" | string;
  id: string;
  title: string;
  description?: string;
  diff?: string;
  sql?: string;
  status?: string;
  before_after?: BeforeAfter[];
};
type Item =
  | { t: "step"; role: string; text: string }
  | { t: "proposal"; p: Proposal }
  | { t: "before_after"; v: BeforeAfter }
  | { t: "text"; md: string }
  | { t: "error"; message: string };

const ROLE_STYLE: Record<string, string> = {
  Koordination: "bg-secondary text-foreground",
  Datenmanagement: "bg-info/10 text-info",
  Klassifikation: "bg-chart-4/10 text-chart-4",
  Qualitätssicherung: "bg-warning/10 text-warning",
  Reporting: "bg-success/10 text-success",
};

type Task = { task_id: number; created_at: string; user: string | null; instruction: string; role: string | null; status: string; model: string | null; proposals: unknown };

export default function AgentPage() {
  const { user } = useUser();
  const tasks = useApi<{ tasks: Task[] }>("/api/agent/aufgaben");
  const [instruction, setInstruction] = useState("");
  const [items, setItems] = useState<Item[]>([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ pct: number; detail?: string } | null>(null);
  const [done, setDone] = useState<{ task_id?: number; model?: string; dry_run?: boolean } | null>(null);
  const [probe, setProbe] = useState(false);
  const [runProbe, setRunProbe] = useState(false);
  const ctrl = useRef<AbortController | null>(null);

  async function send() {
    const text = instruction.trim();
    if (!text || running) return;
    setItems([]);
    setDone(null);
    setProgress(null);
    setRunning(true);
    setRunProbe(probe);
    const c = new AbortController();
    ctrl.current = c;
    try {
      await streamSse(
        "/api/agent",
        { instruction: text, user, ...(probe ? { probe: true } : {}) },
        ({ event, data }) => {
          const d = data as Record<string, unknown>;
          if (event === "step") setItems((x) => [...x, { t: "step", role: String(d.role), text: String(d.text) }]);
          else if (event === "proposal") setItems((x) => [...x, { t: "proposal", p: d as unknown as Proposal }]);
          else if (event === "before_after") setItems((x) => [...x, { t: "before_after", v: d as unknown as BeforeAfter }]);
          else if (event === "text") setItems((x) => [...x, { t: "text", md: String(d.markdown ?? "") }]);
          else if (event === "progress") setProgress({ pct: Number(d.pct ?? 0), detail: d.detail as string | undefined });
          else if (event === "error") setItems((x) => [...x, { t: "error", message: String(d.message) }]);
          else if (event === "done") setDone(d as { task_id?: number; model?: string; dry_run?: boolean });
        },
        c.signal,
      );
    } catch (e) {
      const msg = (e as Error).name === "AbortError" ? "Abgebrochen." : e instanceof ApiError ? e.message : String(e);
      setItems((x) => [...x, { t: "error", message: msg }]);
    } finally {
      setRunning(false);
      tasks.reload();
    }
  }

  const last = [...items].reverse().find((i) => i.t === "step") as Extract<Item, { t: "step" }> | undefined;

  return (
    <PageShell>
      <PageHeading
        title="Agent"
        description="Aufträge in natürlicher Sprache an die Agenten (Koordination, Datenmanagement, Klassifikation, Qualitätssicherung, Reporting). Agenten schlagen Regeln und Code nur vor – wirksam wird nichts ohne Freigabe einer Person."
      />
      <form
        className="flex items-center gap-2 rounded-[26px] border border-border/50 bg-background p-1.5 pl-4 focus-within:border-ring/40"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <textarea
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send();
            }
          }}
          rows={2}
          placeholder="Auftrag, z. B. ein Änderungsauftrag oder eine Sonderauswertung …"
          aria-label="Auftrag an den Agenten"
          className="field-sizing-content max-h-48 min-h-12 w-full flex-1 resize-none bg-transparent py-2 text-sm/6 outline-none placeholder:text-muted-foreground"
        />
        {running ? (
          <Button type="button" size="icon-sm" className="rounded-full" aria-label="Abbrechen" onClick={() => ctrl.current?.abort()}>
            <HugeiconsIcon icon={StopIcon} strokeWidth={2} />
          </Button>
        ) : (
          <Button type="submit" size="icon-sm" className="rounded-full" aria-label="Auftrag senden" disabled={!instruction.trim()}>
            <HugeiconsIcon icon={ArrowUp02Icon} strokeWidth={2} />
          </Button>
        )}
      </form>
      <div className="-mt-3 flex flex-wrap items-center gap-3">
        <Switch checked={probe} onChange={setProbe} label="Probelauf (wird zurückgerollt)" />
        {probe && (
          <span className="rounded-full bg-info/10 px-2 py-0.5 text-xs text-info">
            Alles läuft und wird angezeigt, am Ende aber zurückgerollt – nichts wird gespeichert oder vorgeschlagen.
          </span>
        )}
      </div>
      <div className="-mt-2 flex flex-wrap items-center gap-1.5" aria-label="Beispielaufträge">
        <span className="text-xs text-muted-foreground">Vorlagen (füllt nur das Feld – absenden musst du selbst):</span>
        {[
          ["Auftrag 1", "Auftrag 1: Unterscheide in Statistik und Aggregations-Sheet nicht mehr zwischen Dienstvertrag und freiem Dienstvertrag – nur noch Arbeiter, Angestellte und Beamte, rückwirkend für die ganze Zeitreihe."],
          ["Auftrag 2", "Auftrag 2: Zähle das ganze Monat statt des Stichtags – beschäftigt ist, wer im Berichtsmonat mindestens einen Tag beschäftigt war."],
          ["Auftrag 3", "Auftrag 3: Erstelle die Ministeriums-Lieferung für 07/2026 – Personen mit mindestens 200 Tagen als Arbeiter (DV oder FD) in ÖNACE-Abschnitt C in den letzten zwölf Monaten."],
          ["Freigegebene Aufträge umsetzen", "Setze die freigegebenen Aufträge um"],
          ["Sonderauswertung", "Erstelle eine Sonderauswertung: Arbeiter in Wien nach Altersgruppen"],
        ].map(([label, text]) => (
          <Button key={label} type="button" size="xs" variant="outline" className="rounded-full" disabled={running} onClick={() => setInstruction(text)}>
            {label}
          </Button>
        ))}
      </div>
      <p className="-mt-3 text-xs text-muted-foreground">
        {user ? `Auftrag von ${user}` : "Nicht angemeldet – der Auftrag wird ohne Namen protokolliert."} · Vorschläge erscheinen danach unter{" "}
        <Link href="/freigaben" className="underline underline-offset-4">
          Freigaben
        </Link>
        .
      </p>

      {(items.length > 0 || running) && (
        <Panel
          title={
            <span className="flex items-center gap-2">
              Ablauf
              {runProbe && <span className="rounded-full bg-info/10 px-2 py-0.5 text-xs font-medium text-info">Probelauf – wird zurückgerollt</span>}
            </span>
          }
          action={
            done && (
              <span className="font-mono text-xs text-muted-foreground">
                {done.dry_run ? "zurückgerollt" : done.task_id !== undefined ? `Aufgabe ${done.task_id}` : ""}
              </span>
            )
          }
        >
          {running && progress && (
            <div className="flex flex-col gap-1">
              <Progress value={progress.pct} className="h-1.5" aria-label="Fortschritt" />
              {progress.detail && <span className="text-xs text-muted-foreground">{progress.detail}</span>}
            </div>
          )}
          <ol className="flex flex-col gap-3">
            <AnimatePresence initial={false}>
              {items.map((it, i) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: append-only stream
                <motion.li key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
                  <ItemView item={it} probe={runProbe} />
                </motion.li>
              ))}
            </AnimatePresence>
          </ol>
          {running && <Shimmer className="text-xs">{last ? `${last.role} arbeitet …` : "Auftrag wird gelesen …"}</Shimmer>}
          {done?.model && <span className="text-[11px] text-muted-foreground">{done.model}</span>}
        </Panel>
      )}

      <SectionTitle>Codevorschläge</SectionTitle>
      <p className="-mt-1 max-w-3xl text-xs text-muted-foreground">
        Für Wünsche, die keine bestehende Regel abdeckt (z. B. „Erstelle eine Sonderauswertung: Arbeiter in Wien nach Altersgruppen“ – auch bei
        der Live-Änderung der Jury), schreibt der Agent Code: eine lesbare Python-Datei aus einer geprüften Vorlage, die ohne Sprachmodell
        reproduzierbar rechnet. Sie läuft erst, wenn eine Person genau diese Fassung (SHA-256) freigegeben hat; Anweisung und Ergebnis
        landen im Protokoll (Aufgabenstellung, technische Regel 6). Für die Änderungsaufträge 1–3 braucht es keinen Code – dort reichen Regeln.
      </p>
      <CodeProposals />

      <SectionTitle>Bisherige Aufträge</SectionTitle>
      {tasks.error ? (
        <ErrorState error={tasks.error} onRetry={tasks.reload} what="Aufträge" />
      ) : !tasks.data ? (
        <LoadingState rows={3} />
      ) : tasks.data.tasks.length === 0 ? (
        <EmptyState title="Noch keine Aufträge" />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">Nr.</TableHead>
                <TableHead className="text-xs">Zeitpunkt</TableHead>
                <TableHead className="text-xs">Person</TableHead>
                <TableHead className="text-xs">Auftrag</TableHead>
                <TableHead className="text-xs">Rolle</TableHead>
                <TableHead className="text-xs">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.data.tasks.map((t) => (
                <TableRow key={t.task_id}>
                  <TableCell className="font-mono text-xs">{t.task_id}</TableCell>
                  <TableCell className="text-xs whitespace-nowrap text-muted-foreground">{fmtDateTime(t.created_at)}</TableCell>
                  <TableCell className="text-xs">{t.user ?? "–"}</TableCell>
                  <TableCell className="min-w-64 text-xs">{t.instruction}</TableCell>
                  <TableCell className="text-xs">{t.role ?? "–"}</TableCell>
                  <TableCell>
                    <StatusBadge value={t.status} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </PageShell>
  );
}

function ItemView({ item, probe = false }: { item: Item; probe?: boolean }) {
  if (item.t === "step")
    return (
      <div className="flex items-start gap-2 text-sm">
        <span className={cn("mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium", ROLE_STYLE[item.role] ?? "bg-secondary")}>{item.role}</span>
        <span>{item.text}</span>
      </div>
    );
  if (item.t === "text")
    return (
      <div className="prose-stat">
        <Streamdown mode="static" controls={false}>
          {item.md}
        </Streamdown>
      </div>
    );
  if (item.t === "error")
    return (
      <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
        {item.message}
      </p>
    );
  if (item.t === "before_after") return <BeforeAfterTable rows={[item.v]} />;
  const p = item.p;
  return (
    <div className={cn("flex flex-col gap-3 rounded-xl border p-3", probe ? "border-info/40 border-dashed" : "border-border")}>
      {probe && (
        <div role="note" className="rounded-lg bg-info/10 px-3 py-2 text-xs font-medium text-info">
          Probelauf – nicht gespeichert. Dieser Vorschlag wurde zurückgerollt und kann nicht freigegeben werden.
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{p.kind === "rule" ? "Regelvorschlag" : p.kind === "code" ? "Codevorschlag" : p.kind}</span>
        <span className="font-mono text-xs">{p.id}</span>
        <span className="text-sm font-medium">{p.title}</span>
        {p.status && !probe && (
          <span className="ml-auto">
            <StatusBadge value={p.status} />
          </span>
        )}
      </div>
      {p.description && <p className="text-sm text-muted-foreground">{p.description}</p>}
      {p.before_after && p.before_after.length > 0 && <BeforeAfterTable rows={p.before_after} />}
      {p.sql && <SqlBlock code={p.sql} maxHeight="12rem" />}
      {p.diff && <CodeBlock code={p.diff} lang="diff" maxHeight="20rem" />}
      {!probe && (
        <Button asChild size="sm" variant="outline" className="w-fit">
          <Link href={p.kind === "rule" ? `/freigaben?regel=${p.id}` : "/freigaben"}>Zur Freigabe</Link>
        </Button>
      )}
    </div>
  );
}

function BeforeAfterTable({ rows }: { rows: BeforeAfter[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="text-xs">Kennzahl</TableHead>
            <TableHead className="text-right text-xs">vorher</TableHead>
            <TableHead className="text-right text-xs">nachher (Vorschau)</TableHead>
            <TableHead className="text-right text-xs">Differenz</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r, i) => (
            // biome-ignore lint/suspicious/noArrayIndexKey: label may repeat
            <TableRow key={i}>
              <TableCell className="text-xs">{r.label}</TableCell>
              <TableCell className="text-right font-mono text-xs tabular-nums">{fmt(r.before)}</TableCell>
              <TableCell className="text-right font-mono text-xs tabular-nums">{r.after === null ? "erst nach Freigabe" : fmt(r.after)}</TableCell>
              <TableCell className="text-right font-mono text-xs tabular-nums">
                {r.before !== null && r.after !== null ? (r.after - r.before > 0 ? "+" : "") + fmt(r.after - r.before) : "–"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

type CodeRow = { proposal_id: string; instruction: string; path: string; sha256: string; status: string; executions: number; created_at?: string };

function CodeProposals() {
  const { user } = useUser();
  const list = useApi<{ proposals: CodeRow[] }>("/api/code");
  const [openId, setOpenId] = useState<string | null>(null);
  const detail = useApi<{ diff?: string; unchanged?: boolean; executions?: { execution_id: number; status: string; finished_at?: string; result?: unknown }[] }>(
    openId ? `/api/code/${openId}` : null,
  );
  const [exec, setExec] = useState<{ id: string; lines: string[]; error?: string; done?: boolean } | null>(null);

  async function execute(id: string) {
    if (!user) return;
    setExec({ id, lines: [] });
    try {
      await streamSse("/api/code/" + id + "/ausfuehren", { person: user }, ({ event, data }) => {
        const d = data as Record<string, unknown>;
        if (event === "progress") setExec((e) => e && { ...e, lines: [...e.lines, `${fmt(Number(d.pct))} % · ${String(d.detail ?? "")}`] });
        else if (event === "error") setExec((e) => e && { ...e, error: String(d.message) });
        else if (event === "result") setExec((e) => e && { ...e, done: true });
      });
    } catch (e) {
      setExec((x) => x && { ...x, error: e instanceof ApiError ? e.message : String(e) });
    }
    list.reload();
  }

  if (list.error) return <ErrorState error={list.error} onRetry={list.reload} what="Codevorschläge" />;
  if (!list.data) return <LoadingState rows={2} />;
  if (!list.data.proposals.length) return <EmptyState title="Keine Codevorschläge" description="Entstehen, wenn ein Auftrag eine Sonderauswertung verlangt." />;
  return (
    <div className="flex flex-col gap-2">
      {list.data.proposals.map((p) => (
        <Panel
          key={p.proposal_id}
          title={
            <span className="flex items-center gap-2">
              <span className="font-mono text-xs">{p.proposal_id}</span>
              <span>{p.instruction}</span>
            </span>
          }
          description={<span className="font-mono">{p.path} · {fmt(p.executions)} Ausführungen</span>}
          action={<StatusBadge value={p.status} />}
        >
          <div className="flex flex-wrap gap-2">
            <Button size="xs" variant="outline" onClick={() => setOpenId(openId === p.proposal_id ? null : p.proposal_id)}>
              {openId === p.proposal_id ? "Code ausblenden" : "Code anzeigen"}
            </Button>
            <Button
              size="xs"
              disabled={p.status !== "approved" || !user || (exec?.id === p.proposal_id && !exec.done && !exec.error)}
              title={p.status !== "approved" ? "Erst nach Freigabe durch eine Person ausführbar" : !user ? "Bitte anmelden" : undefined}
              onClick={() => p.status === "approved" && execute(p.proposal_id)}
            >
              Ausführen
            </Button>
            {p.status !== "approved" && <span className="self-center text-xs text-muted-foreground">Ausführen erst nach Freigabe</span>}
            {p.status === "proposed" && (
              <Button asChild size="xs" variant="outline">
                <Link href="/freigaben">Zur Freigabe</Link>
              </Button>
            )}
          </div>
          {openId === p.proposal_id &&
            (detail.data ? (
              <>
                {detail.data.unchanged === false && <p className="text-xs text-destructive">Datei seit dem Vorschlag verändert – Ausführung wird verweigert.</p>}
                <CodeBlock code={detail.data.diff ?? ""} lang="diff" maxHeight="24rem" />
              </>
            ) : detail.error ? (
              <ErrorState error={detail.error} />
            ) : (
              <LoadingState rows={2} />
            ))}
          {exec?.id === p.proposal_id && (
            <div className="flex flex-col gap-1 text-xs">
              {exec.lines.map((l, i) => (
                // biome-ignore lint/suspicious/noArrayIndexKey: progress lines
                <span key={i} className="text-muted-foreground">
                  {l}
                </span>
              ))}
              {exec.error && <span className="text-destructive">{exec.error}</span>}
              {exec.done && <span className="text-success">Ausgeführt.</span>}
            </div>
          )}
        </Panel>
      ))}
    </div>
  );
}
