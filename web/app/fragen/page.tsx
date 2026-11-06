"use client";

import { ArrowUp02Icon, Delete02Icon, Search01Icon, StopIcon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { AnimatePresence, motion } from "motion/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Streamdown } from "streamdown";
import { useApi } from "@/hooks/use-api";
import { ApiError, streamSse } from "@/lib/api";
import type { Health } from "@/lib/types";
import { cn } from "@/lib/utils";
import { AnswerCard, type AnswerCardData } from "@/components/chat/answer-card";
import { useUser } from "@/components/shell/user-provider";
import { FixLinks } from "@/components/stat/fix-links";
import { ProgressCard } from "@/components/stat/progress-card";
import { Shimmer } from "@/components/stat/shimmer";
import { AbstentionState } from "@/components/stat/states";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

type Clarification = {
  term: string;
  word?: string;
  question: string;
  options: { id: string; label: string; definition: string; is_default?: boolean }[];
  answered?: Record<string, string>;
  pending?: Record<string, unknown>;
};

/** Request options for one streamed answer. */
type AskOptions = {
  question: string;
  reading?: Record<string, string>;
  /** re-use this turn (chained Rückfragen) instead of appending a new one */
  turnId?: string;
  previous?: Record<string, unknown>;
  handling?: Record<string, string>;
  free_text?: Record<string, string>;
  /** short description of a recalculation, shown in the user bubble */
  recalc?: string;
  labels?: Turn["labels"];
};

type Turn = {
  id: string;
  question: string;
  reading?: Record<string, string>;
  /** labels of answered Rückfragen: term → {word, label} */
  labels?: Record<string, { word?: string; label: string }>;
  recalc?: string;
  /** shown when a free-text answer could not be mapped to an offered reading */
  freeHint?: string;
  status: string[];
  card?: AnswerCardData;
  text?: string;
  clarification?: Clarification;
  abstention?: { reason: string; kind?: string };
  error?: string;
  done?: { answer_id?: number | string; model?: string };
  running: boolean;
};

const ROLES = ["Jury", "Datenmanagement", "Klassifikation", "Qualitätssicherung", "Reporting"];
const STORE = "statagent-chat";

export default function QuestionsPage() {
  const { user } = useUser();
  const health = useApi<Health>("/api/health");
  const suggestions = useApi<{ suggestions: { text_de: string; role: string }[] }>("/api/fragen/vorschlaege");
  const [role, setRole] = useState("Jury");
  const [text, setText] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [conversationId, setConversationId] = useState("");
  const ctrl = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  const busy = turns.some((t) => t.running);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(STORE);
      if (saved) {
        const s = JSON.parse(saved) as { id: string; turns: Turn[] };
        setConversationId(s.id);
        setTurns(s.turns.map((t) => ({ ...t, running: false })));
        return;
      }
    } catch {
      /* ignore */
    }
    setConversationId(crypto.randomUUID());
  }, []);
  useEffect(() => {
    if (!conversationId) return;
    try {
      sessionStorage.setItem(STORE, JSON.stringify({ id: conversationId, turns: turns.filter((t) => !t.running) }));
    } catch {
      /* ignore */
    }
  }, [turns, conversationId]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [turns]);

  const ask = useCallback(
    async (o: AskOptions) => {
      const { question, reading } = o;
      const previous =
        o.previous ?? [...turns].reverse().find((t) => t.id !== o.turnId && t.card?.params)?.card?.params;
      const id = o.turnId ?? crypto.randomUUID();
      const patch = (p: Partial<Turn> | ((t: Turn) => Partial<Turn>)) =>
        setTurns((ts) => ts.map((t) => (t.id === id ? { ...t, ...(typeof p === "function" ? p(t) : p) } : t)));
      const fresh = {
        reading,
        status: [] as string[],
        running: true,
        card: undefined,
        text: undefined,
        clarification: undefined,
        abstention: undefined,
        error: undefined,
        done: undefined,
        freeHint: undefined,
      };
      if (o.turnId) patch(fresh);
      else setTurns((ts) => [...ts, { id, question, recalc: o.recalc, labels: o.labels, ...fresh }]);
      const c = new AbortController();
      ctrl.current = c;
      try {
        await streamSse(
          "/api/fragen",
          {
            question,
            user: user ?? null,
            role,
            conversation_id: conversationId,
            previous,
            ...(reading && Object.keys(reading).length ? { reading } : {}),
            ...(o.handling ? { handling: o.handling } : {}),
            ...(o.free_text ? { free_text: o.free_text } : {}),
          },
          ({ event, data }) => {
            const d = data as Record<string, unknown>;
            if (event === "status") patch((t) => ({ status: [...t.status, String(d.text)] }));
            else if (event === "card") patch({ card: d as unknown as AnswerCardData });
            else if (event === "text") patch((t) => ({ text: (t.text ?? "") + String(d.markdown ?? "") }));
            else if (event === "clarification") patch({ clarification: d as unknown as Clarification });
            else if (event === "abstention") patch({ abstention: { reason: String(d.reason), kind: d.kind as string | undefined } });
            else if (event === "error") patch({ error: String(d.message ?? "Fehler") });
            else if (event === "done") patch({ done: d as Turn["done"] });
          },
          c.signal,
        );
      } catch (e) {
        if ((e as Error).name === "AbortError") patch({ error: "Abgebrochen." });
        else patch({ error: e instanceof ApiError ? (e.notAvailable ? "Die Frage-Schnittstelle ist noch nicht verfügbar." : e.message) : String(e) });
      } finally {
        patch({ running: false });
      }
    },
    [turns, user, role, conversationId],
  );

  // deep link /fragen?frage=… asks the question once (links from other pages, demos)
  const deepLinked = useRef(false);
  useEffect(() => {
    if (deepLinked.current || !conversationId) return;
    const q = new URLSearchParams(window.location.search).get("frage");
    if (!q) return;
    deepLinked.current = true;
    window.history.replaceState(null, "", "/fragen");
    void ask({ question: q });
  }, [conversationId, ask]);

  const submit = () => {
    const q = text.trim();
    if (!q || busy) return;
    setText("");
    void ask({ question: q });
  };

  /** Rückfrage answered: resend the same question with all readings so far (chained). */
  const pick = (t: Turn, c: Clarification, optionId: string) => {
    const label = c.options.find((x) => x.id === optionId)?.label ?? optionId;
    setTurns((ts) => ts.map((x) => (x.id === t.id ? { ...x, labels: { ...(x.labels ?? {}), [c.term]: { word: c.word, label } } } : x)));
    void ask({ question: t.question, reading: { ...(c.answered ?? {}), ...(t.reading ?? {}), [c.term]: optionId }, turnId: t.id });
  };
  /** Rückfrage answered in own words: re-ask the question with the clarification appended (the parser reads it again). */
  const freeAnswer = (t: Turn, c: Clarification, answer: string) => {
    // deterministic mapping of the own words onto one offered reading (keywords of the option labels)
    const match = matchOption(answer, c.options);
    if (match) {
      setTurns((ts) =>
        ts.map((x) =>
          x.id === t.id ? { ...x, labels: { ...(x.labels ?? {}), [c.term]: { word: c.word, label: `${match.label} (aus „${answer}“)` } } } : x,
        ),
      );
      void ask({ question: t.question, reading: { ...(c.answered ?? {}), ...(t.reading ?? {}), [c.term]: match.id }, turnId: t.id });
      return;
    }
    setTurns((ts) =>
      ts.map((x) =>
        x.id === t.id
          ? {
              ...x,
              freeHint: `„${answer}“ lässt sich keiner der angebotenen Lesarten eindeutig zuordnen – bitte eine Lesart wählen oder die Frage neu formulieren. Es wird nichts geraten.`,
            }
          : x,
      ),
    );
  };
  /** Change an earlier answer: resend without that reading – the Rückfrage comes again. */
  const unpick = (t: Turn, term: string) => {
    const reading = { ...(t.reading ?? {}) };
    delete reading[term];
    void ask({ question: t.question, reading, turnId: t.id });
  };
  /** Recalculate a card with a user-chosen data-quality handling (new turn, official card stays visible). */
  const recalc = (t: Turn, handling: Record<string, string>, freeText: Record<string, string>, summary: string) => {
    if (!t.card) return;
    void ask({
      question: t.question,
      previous: t.card.params,
      reading: (t.card.readings as Record<string, string> | undefined) ?? t.reading,
      handling,
      free_text: Object.keys(freeText).length ? freeText : undefined,
      recalc: summary,
      labels: t.labels,
    });
  };

  const chips = (suggestions.data?.suggestions ?? []).filter((s) => s.role === "alle" || s.role === role);

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-49px)] w-full max-w-[860px] flex-col px-4 md:px-8">
      <div className="flex flex-1 flex-col gap-6 py-8">
        {turns.length === 0 ? (
          <div className="flex flex-col gap-2 pt-[8vh]">
            <h1 className="text-2xl font-semibold">Fragen an die Statistik</h1>
            <p className="max-w-xl text-sm text-muted-foreground">
              Zahlen kommen nur aus SQL-Abfragen auf den Bestand. Jede Antwort zeigt Definition, Abfrage und Quellennachweis; jede Zahl im Text wird gegen
              ihre Abfrage geprüft. Ist eine Frage mehrdeutig, kommt eine Rückfrage – fehlen Daten, wird das gesagt.
            </p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {turns.map((t) => (
              <motion.div key={t.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex flex-col gap-3">
                <div className="ml-auto flex max-w-[85%] flex-col items-end gap-1">
                  <div className="rounded-2xl bg-muted px-4 py-2.5 text-sm">{t.question}</div>
                  {t.recalc && <span className="text-xs text-muted-foreground">Neu berechnen: {t.recalc}</span>}
                </div>
                <TurnView
                  turn={t}
                  onPick={(c, id) => pick(t, c, id)}
                  onFreeAnswer={(c, text) => freeAnswer(t, c, text)}
                  onUnpick={(term) => unpick(t, term)}
                  onRecalc={(h, ft, summary) => recalc(t, h, ft, summary)}
                  disabled={busy}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        )}
        <div ref={bottom} />
      </div>
      <div className="sticky bottom-0 flex flex-col gap-2 bg-background/95 pt-2 pb-4 backdrop-blur">
        <div className="flex flex-wrap items-center gap-2">
          <ToggleGroup type="single" value={role} onValueChange={(v) => v && setRole(v)} variant="outline" size="sm" aria-label="Rolle" className="flex-wrap">
            {ROLES.map((r) => (
              <ToggleGroupItem key={r} value={r} className="px-2.5 text-xs">
                {r}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          {turns.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="ml-auto text-xs"
              disabled={busy}
              onClick={() => {
                setTurns([]);
                setConversationId(crypto.randomUUID());
              }}
            >
              <HugeiconsIcon icon={Delete02Icon} strokeWidth={2} data-icon="inline-start" />
              Neues Gespräch
            </Button>
          )}
        </div>
        {chips.length > 0 && (
          <div className="flex gap-1.5 overflow-x-auto pb-1" aria-label="Beispielfragen (füllen das Eingabefeld)">
            {chips.map((s) => (
              <Button
                key={s.text_de}
                variant="outline"
                size="xs"
                className="shrink-0 rounded-full font-normal"
                onClick={() => {
                  setText(s.text_de);
                  input.current?.focus();
                }}
              >
                {s.text_de}
              </Button>
            ))}
          </div>
        )}
        {suggestions.error && !suggestions.error.notAvailable && <p className="text-xs text-muted-foreground">Beispielfragen nicht verfügbar.</p>}
        <form
          className="flex items-center gap-2 rounded-[26px] border border-border/50 bg-background p-1.5 pl-4 focus-within:border-ring/40"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <textarea
            ref={input}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={1}
            maxLength={2000}
            placeholder="Frage zur Beschäftigungsstatistik …"
            aria-label="Frage"
            className="field-sizing-content max-h-40 min-h-9 w-full flex-1 resize-none bg-transparent py-2 text-sm/6 outline-none placeholder:text-muted-foreground"
          />
          {busy ? (
            <Button type="button" size="icon-sm" className="rounded-full" aria-label="Abbrechen" onClick={() => ctrl.current?.abort()}>
              <HugeiconsIcon icon={StopIcon} strokeWidth={2} />
            </Button>
          ) : (
            <Button type="submit" size="icon-sm" className="rounded-full" aria-label="Frage senden" disabled={!text.trim()}>
              <HugeiconsIcon icon={ArrowUp02Icon} strokeWidth={2} />
            </Button>
          )}
        </form>
        <p className="text-center text-[11px] text-muted-foreground">
          {user ? `Angemeldet als ${user}` : `Nicht angemeldet – Fragen werden als „${health.data?.fragen_person ?? "Gast"}“ protokolliert`} · Antworten und Fragen werden protokolliert.
        </p>
      </div>
    </div>
  );
}

function TurnView({
  turn,
  onPick,
  onFreeAnswer,
  onUnpick,
  onRecalc,
  disabled,
}: {
  turn: Turn;
  onPick: (c: Clarification, id: string) => void;
  onFreeAnswer: (c: Clarification, text: string) => void;
  onUnpick: (term: string) => void;
  onRecalc: (handling: Record<string, string>, freeText: Record<string, string>, summary: string) => void;
  disabled: boolean;
}) {
  const last = turn.status[turn.status.length - 1];
  const answered = Object.entries(turn.reading ?? {});
  return (
    <div className="flex flex-col gap-3">
      {answered.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5" aria-label="Gewählte Lesarten">
          {answered.map(([term, id], i) => {
            const l = turn.labels?.[term];
            return (
              <button
                type="button"
                key={term}
                disabled={disabled}
                onClick={() => onUnpick(term)}
                title="Antwort ändern – die Rückfrage wird erneut gestellt"
                className="flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-xs hover:bg-muted disabled:opacity-50"
              >
                <span className="text-muted-foreground">
                  {i + 1}. Lesart{l?.word ? ` „${l.word}“` : ` ${term}`}:
                </span>
                <span className="font-medium">{l?.label ?? id}</span>
                <span aria-hidden="true" className="text-muted-foreground">
                  ×
                </span>
              </button>
            );
          })}
        </div>
      )}
      {turn.running && turn.recalc && (
        <ProgressCard
          title="Neuberechnung mit eigener Behandlung"
          status="running"
          steps={turn.status.map((s) => ({ step: s, pct: Number.NaN }))}
          pct={null}
        />
      )}
      {turn.running && !turn.recalc && last && !turn.card && (
        <div role="status" aria-live="polite" className="flex items-center gap-2">
          <HugeiconsIcon icon={Search01Icon} size={16} strokeWidth={2} className="text-muted-foreground" aria-hidden="true" />
          <Shimmer className="text-xs">{last}</Shimmer>
        </div>
      )}
      {turn.running && !last && <Shimmer className="text-xs">Verbindung wird aufgebaut …</Shimmer>}
      {!turn.running && turn.status.length > 0 && (
        <details className="text-xs text-muted-foreground">
          <summary className="w-fit cursor-pointer hover:text-foreground">{turn.status.length} {turn.status.length === 1 ? "Schritt" : "Schritte"}</summary>
          <ol className="mt-1 ml-4 list-decimal">
            {turn.status.map((s, i) => (
              // biome-ignore lint/suspicious/noArrayIndexKey: ordered steps
              <li key={i}>{s}</li>
            ))}
          </ol>
        </details>
      )}
      {turn.clarification && (
        <div className="flex flex-col gap-2 rounded-2xl border border-border p-4">
          <p className="text-xs text-muted-foreground">
            Rückfrage {answered.length + 1}
            {turn.clarification.word ? ` · „${turn.clarification.word}“` : ""}
          </p>
          <p className="text-sm font-medium">{turn.clarification.question}</p>
          <div className="flex flex-col gap-1.5">
            {turn.clarification.options.map((o) => (
              <button
                type="button"
                key={o.id}
                disabled={disabled}
                onClick={() => onPick(turn.clarification!, o.id)}
                className={cn(
                  "flex flex-col items-start gap-0.5 rounded-xl border border-border px-3 py-2 text-left transition-colors hover:bg-muted disabled:opacity-50",
                  o.is_default && "border-foreground/30",
                )}
              >
                <span className="text-sm font-medium">
                  {o.label}
                  {o.is_default && <span className="ml-2 text-xs font-normal text-muted-foreground">Standard</span>}
                </span>
                <span className="text-xs text-muted-foreground">{o.definition}</span>
              </button>
            ))}
          </div>
          <FreeAnswer disabled={disabled} onSubmit={(text) => onFreeAnswer(turn.clarification!, text)} />
          {turn.freeHint && <p className="text-xs text-warning">{turn.freeHint}</p>}
        </div>
      )}
      {turn.card && (
        <AnswerCard
          card={turn.card}
          question={turn.question}
          answerId={turn.done?.answer_id ?? turn.id}
          onRecalc={turn.running ? undefined : onRecalc}
          recalcDisabled={disabled}
        />
      )}
      {turn.text && (
        <div className="prose-stat text-sm">
          <Streamdown mode={turn.running ? "streaming" : "static"} controls={false}>
            {turn.text}
          </Streamdown>
        </div>
      )}
      {turn.abstention && <AbstentionState kind={turn.abstention.kind} reason={turn.abstention.reason} />}
      {turn.error && (
        <div role="alert" className="flex flex-col gap-2 rounded-xl border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {turn.error}
          <FixLinks message={turn.error} />
        </div>
      )}
      {turn.done?.model && <span className="text-[11px] text-muted-foreground">{turn.done.model}</span>}
    </div>
  );
}

/** „Anders gemeint?“ – free-text answer to a Rückfrage (sent back with the question, never interpreted as a number). */
function FreeAnswer({ onSubmit, disabled }: { onSubmit: (text: string) => void; disabled: boolean }) {
  const [text, setText] = useState("");
  return (
    <form
      className="flex items-center gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (text.trim()) onSubmit(text.trim());
      }}
    >
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
        maxLength={300}
        placeholder="Anders gemeint? In eigenen Worten beschreiben …"
        aria-label="Rückfrage in eigenen Worten beantworten"
        className="h-9 flex-1 rounded-xl border border-border bg-transparent px-3 text-sm outline-none placeholder:text-muted-foreground focus:border-ring/40"
      />
      <Button type="submit" size="sm" variant="outline" disabled={disabled || !text.trim()}>
        Senden
      </Button>
    </form>
  );
}

const STOP = new Set(["und", "oder", "nur", "der", "die", "das", "des", "den", "dem", "ein", "eine", "mit", "ohne", "von", "pro", "je", "als", "im", "in", "am", "zum", "zur", "bzw"]);
const tokens = (t: string) =>
  t
    .toLowerCase()
    .replace(/[^a-zäöüß0-9 -]/g, " ")
    .split(/[\s-]+/)
    .filter((w) => w.length >= 4 && !STOP.has(w));

/** Pick the one option whose label words occur in the free text (stems ≥ 5 chars); null if none or ambiguous. */
function matchOption(text: string, options: Clarification["options"]): Clarification["options"][number] | null {
  const words = tokens(text);
  const hit = (w: string) => words.some((x) => x.startsWith(w.slice(0, 5)) || w.startsWith(x.slice(0, 5)));
  const scored = options.map((o) => {
    const lw = tokens(o.label);
    const lab = lw.filter(hit).length;
    // exclusive words like „nur“ in the text favour the narrower option
    const narrow = /\bnur\b/i.test(text) && /\bnur\b/i.test(o.label) ? 0.5 : 0;
    return { o, score: lab + narrow, full: lw.length > 0 && lab === lw.length };
  });
  const best = Math.max(...scored.map((x) => x.score));
  if (best < 1) return null;
  const top = scored.filter((x) => x.score === best);
  if (top.length === 1) return top[0].o;
  const full = top.filter((x) => x.full);
  return full.length === 1 ? full[0].o : null;
}
