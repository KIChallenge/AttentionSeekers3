"use client";

import { Cancel01Icon, Tick02Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { toast } from "sonner";
import { useApi } from "@/hooks/use-api";
import { ApiError, apiPost } from "@/lib/api";
import { fmtDateTime, ruleSetLabel } from "@/lib/format";
import type { Approval, CodeProposal, Rule } from "@/lib/types";
import { cn } from "@/lib/utils";
import { LoginForm } from "@/components/shell/login-form";
import { useUser } from "@/components/shell/user-provider";
import { StatusBadge } from "@/components/stat/badges";
import { CodeBlock, CopyButton } from "@/components/stat/code-block";
import { FixLinks } from "@/components/stat/fix-links";
import { TrialApply } from "@/components/stat/trial-apply";
import { PageHeading, PageShell, Panel, SectionTitle } from "@/components/stat/page-shell";
import { EmptyState, ErrorState, LoadingState } from "@/components/stat/states";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";

type Inbox = { approvals: Approval[]; pending_rules: Rule[]; pending_code: CodeProposal[] };
type Pending = { kind: "rule" | "code"; id: string; title: string; approve: boolean };

export default function Page() {
  return (
    <Suspense fallback={<PageShell><LoadingState /></PageShell>}>
      <ApprovalsPage />
    </Suspense>
  );
}

function ApprovalsPage() {
  const { user } = useUser();
  const inbox = useApi<Inbox>("/api/freigaben");
  const allRules = useApi<{ rules: Rule[] }>("/api/regeln");
  const highlight = useSearchParams().get("regel");
  const [pending, setPending] = useState<Pending | null>(null);

  useEffect(() => {
    if (highlight && inbox.data) document.getElementById(`regel-${highlight}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [highlight, inbox.data]);

  const decided = (allRules.data?.rules ?? []).filter((r) => r.status !== "proposed");

  return (
    <PageShell>
      <PageHeading
        title="Freigaben"
        description="Regeln, Code und Veröffentlichungen wirken erst, wenn eine namentlich genannte Person sie freigibt (T7). Agenten schlagen nur vor. Jede Entscheidung landet im Protokoll."
      />
      {!user && (
        <Panel title="Anmeldung erforderlich" description="Für Freigaben und Ablehnungen wird der Name einer Person benötigt. Platzhalter wie „Team“ lehnt das System ab.">
          <LoginForm />
        </Panel>
      )}
      {inbox.error ? (
        <ErrorState error={inbox.error} onRetry={inbox.reload} what="Freigaben" />
      ) : !inbox.data ? (
        <LoadingState rows={6} />
      ) : (
        <>
          <SectionTitle>Offene Regeln ({inbox.data.pending_rules.length})</SectionTitle>
          {inbox.data.pending_rules.length === 0 ? (
            <EmptyState title="Keine offenen Regeln" />
          ) : (
            <div className="flex flex-col gap-3">
              {inbox.data.pending_rules.map((r) => (
                <div key={r.rule_id} id={`regel-${r.rule_id}`}>
                  <Panel
                    className={cn(highlight === r.rule_id && "border-foreground/40")}
                    title={
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs">{r.rule_id}</span>
                        <span>{r.title}</span>
                      </span>
                    }
                    description={`${r.problem_id ?? ""} · Regelwerk ${ruleSetLabel(r.rule_set)} · vorgeschlagen von ${r.created_by ?? "–"} · ${fmtDateTime(r.created_at)}`}
                    action={<StatusBadge value={r.status} />}
                  >
                    <p className="text-sm">{r.description}</p>
                    {r.assumption && (
                      <p className="text-sm">
                        <span className="font-medium">Annahme:</span> {r.assumption}
                      </p>
                    )}
                    {r.justification && (
                      <p className="text-xs text-muted-foreground">
                        <span className="font-medium text-foreground">Begründung:</span> {r.justification}
                      </p>
                    )}
                    <details className="text-xs">
                      <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                        Aktion <span className="font-mono">{r.action}</span> · Parameter
                      </summary>
                      <pre className="mt-2 overflow-x-auto rounded-xl border border-border bg-muted p-3 font-mono text-xs">{JSON.stringify(r.parameters ?? {}, null, 2)}</pre>
                    </details>
                    <TrialApply rule={r} />
                    <DecisionButtons onDecide={(approve) => setPending({ kind: "rule", id: r.rule_id, title: r.title, approve })} />
                  </Panel>
                </div>
              ))}
            </div>
          )}

          <SectionTitle>Offener Code ({inbox.data.pending_code.length})</SectionTitle>
          {inbox.data.pending_code.length === 0 ? (
            <EmptyState title="Keine offenen Codevorschläge" description="Codevorschläge entstehen, wenn der Agent eine Sonderauswertung vorschlägt." />
          ) : (
            <div className="flex flex-col gap-3">
              {inbox.data.pending_code.map((c) => (
                <CodeItem key={String(c.proposal_id)} proposal={c} onDecide={(approve) => setPending({ kind: "code", id: String(c.proposal_id), title: c.instruction, approve })} />
              ))}
            </div>
          )}

          <PublishPanel />

          <SectionTitle>Entscheidungen ({inbox.data.approvals.length})</SectionTitle>
          <div className="overflow-x-auto rounded-xl border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Zeitpunkt</TableHead>
                  <TableHead className="text-xs">Objekt</TableHead>
                  <TableHead className="text-xs">Entscheidung</TableHead>
                  <TableHead className="text-xs">Person</TableHead>
                  <TableHead className="text-xs">Kommentar</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {inbox.data.approvals.map((a) => (
                  <TableRow key={a.approval_id}>
                    <TableCell className="text-xs whitespace-nowrap text-muted-foreground">{fmtDateTime(a.decided_at)}</TableCell>
                    <TableCell className="max-w-72 truncate font-mono text-xs" title={a.object_id}>
                      {a.object_type}: {a.object_id}
                    </TableCell>
                    <TableCell>
                      <StatusBadge value={a.decision} />
                    </TableCell>
                    <TableCell className="text-xs font-medium">{a.person}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{a.comment ?? "–"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {decided.length > 0 && (
            <>
              <SectionTitle>Entschiedene Regeln</SectionTitle>
              <div className="flex flex-col gap-2">
                {decided.map((r) => (
                  <div
                    key={r.rule_id}
                    id={`regel-${r.rule_id}`}
                    className={cn("flex flex-wrap items-center gap-2 rounded-xl border border-border px-3 py-2 text-sm", highlight === r.rule_id && "border-foreground/40")}
                  >
                    <span className="font-mono text-xs">{r.rule_id}</span>
                    <span className="min-w-0 flex-1">{r.title}</span>
                    <StatusBadge value={r.status} label={r.status_label} />
                    <span className="text-xs text-muted-foreground">
                      {r.approved_by ? `${r.approved_by} · ${fmtDateTime(r.approved_at)}` : ""}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
      <DecisionDialog
        pending={pending}
        onClose={() => setPending(null)}
        onDone={() => {
          inbox.reload();
          allRules.reload();
        }}
      />
    </PageShell>
  );
}

function DecisionButtons({ onDecide }: { onDecide: (approve: boolean) => void }) {
  const { user } = useUser();
  return (
    <div className="flex flex-wrap items-center gap-2 pt-1">
      <Button size="sm" onClick={() => onDecide(true)} disabled={!user}>
        <HugeiconsIcon icon={Tick02Icon} strokeWidth={2} data-icon="inline-start" />
        Freigeben
      </Button>
      <Button size="sm" variant="outline" onClick={() => onDecide(false)} disabled={!user}>
        <HugeiconsIcon icon={Cancel01Icon} strokeWidth={2} data-icon="inline-start" />
        Ablehnen
      </Button>
      {!user && <span className="text-xs text-muted-foreground">Bitte zuerst anmelden.</span>}
    </div>
  );
}

function CodeItem({ proposal, onDecide }: { proposal: CodeProposal; onDecide: (approve: boolean) => void }) {
  const [open, setOpen] = useState(false);
  const detail = useApi<CodeProposal & { unchanged?: boolean }>(open ? `/api/code/${proposal.proposal_id}` : null);
  return (
    <Panel
      title={
        <span className="flex items-center gap-2">
          <span className="font-mono text-xs">{proposal.proposal_id}</span>
          <span>{proposal.instruction}</span>
        </span>
      }
      description={
        <span className="flex flex-wrap items-center gap-1 font-mono">
          {proposal.path} · SHA-256 <span title={proposal.sha256}>{proposal.sha256?.slice(0, 16)}…</span>
          {proposal.sha256 && <CopyButton text={proposal.sha256} label="SHA-256 kopieren" />}
        </span>
      }
      action={<StatusBadge value={proposal.status} />}
    >
      <Button variant="outline" size="xs" className="w-fit" onClick={() => setOpen((o) => !o)}>
        {open ? "Code ausblenden" : "Code anzeigen (diff)"}
      </Button>
      {open &&
        (detail.error ? (
          <ErrorState error={detail.error} what="Codevorschlag" />
        ) : !detail.data ? (
          <LoadingState rows={3} />
        ) : (
          <>
            {detail.data.unchanged === false ? (
              <p className="text-xs text-destructive">Achtung: Die Datei wurde seit dem Vorschlag verändert (SHA-256 stimmt nicht mehr) – Ausführung wird verweigert.</p>
            ) : detail.data.unchanged === true ? (
              <p className="text-xs text-success">Datei unverändert seit dem Vorschlag (SHA-256 geprüft).</p>
            ) : null}
            <CodeBlock code={detail.data.diff ?? detail.data.content ?? ""} lang="diff" maxHeight="28rem" />
          </>
        ))}
      <DecisionButtons onDecide={onDecide} />
      <div className="flex items-center gap-2">
        <Button size="xs" variant="outline" disabled title="Erst nach Freigabe durch eine Person ausführbar">
          Ausführen
        </Button>
        <span className="text-xs text-muted-foreground">Ausführen erst nach Freigabe – läuft ohne Sprachmodell, nur mit unveränderter Datei.</span>
      </div>
    </Panel>
  );
}

function DecisionDialog({ pending, onClose, onDone }: { pending: Pending | null; onClose: () => void; onDone: () => void }) {
  const { user } = useUser();
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    setComment("");
    setError(null);
  }, [pending]);
  async function decide() {
    if (!pending) return;
    setBusy(true);
    setError(null);
    try {
      const path = pending.kind === "rule" ? `/api/regeln/${pending.id}/entscheidung` : `/api/code/${pending.id}/entscheidung`;
      const r = await apiPost<{ next?: string }>(path, { person: user ?? "", approve: pending.approve, comment: comment || null });
      toast.success(`${pending.id} ${pending.approve ? "freigegeben" : "abgelehnt"} von ${user}`, { description: r.next ? `Nächster Schritt: ${r.next}` : undefined });
      onDone();
      onClose();
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : String(e);
      setError(msg);
      toast.error("Entscheidung abgelehnt", { description: msg });
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog open={pending !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {pending?.id} {pending?.approve ? "freigeben" : "ablehnen"}?
          </DialogTitle>
          <DialogDescription>
            {pending?.title}
            <br />
            Entscheidung durch <span className="font-medium text-foreground">{user ?? "–"}</span>. Sie wird mit Zeitpunkt im Protokoll festgehalten und ist
            nicht anonym.
          </DialogDescription>
        </DialogHeader>
        <Textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Kommentar / Anweisung (optional, erscheint im Protokoll)" aria-label="Kommentar" />
        {error && (
          <div role="alert" className="flex flex-col gap-2 rounded-xl border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            {error}
            <FixLinks message={error} />
          </div>
        )}
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Abbrechen</Button>
          </DialogClose>
          <Button onClick={decide} disabled={busy || !user} variant={pending?.approve ? "default" : "destructive"}>
            {busy ? "Wird gespeichert …" : pending?.approve ? "Freigeben" : "Ablehnen"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PublishPanel() {
  const { user } = useUser();
  const [ruleSet, setRuleSet] = useState("basis");
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function publish() {
    setBusy(true);
    setError(null);
    try {
      const r = await apiPost<{ published: string[] }>("/api/veroeffentlichen", { person: user ?? "", regelwerk: ruleSet });
      toast.success(`${r.published.length} Monate veröffentlicht von ${user}`);
      setOpen(false);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : String(e);
      setError(msg);
      toast.error("Veröffentlichung abgelehnt", { description: msg });
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Panel
        title="Monate veröffentlichen"
        description="Vorläufige Monatsergebnisse werden durch eine Person veröffentlicht. Spätere Lieferungen ändern veröffentlichte Werte nicht, sondern erscheinen als Revisionsbedarf."
        action={
          <Button size="sm" variant="outline" disabled={!user} onClick={() => setOpen(true)}>
            Veröffentlichen …
          </Button>
        }
      >
        <span className="text-xs text-muted-foreground">Regelwerk wählen und bestätigen; die Schnittstelle prüft den Namen.</span>
      </Panel>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Alle vorläufigen Monate veröffentlichen?</DialogTitle>
            <DialogDescription>
              Regelwerk „{ruleSetLabel(ruleSet)}“ · Entscheidung durch <span className="font-medium text-foreground">{user}</span>.
            </DialogDescription>
          </DialogHeader>
          <div className="flex gap-2">
            {["basis", "auftraege"].map((r) => (
              <Button key={r} size="sm" variant={r === ruleSet ? "default" : "outline"} onClick={() => setRuleSet(r)}>
                {ruleSetLabel(r)}
              </Button>
            ))}
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Abbrechen</Button>
            </DialogClose>
            <Button onClick={publish} disabled={busy || !user}>
              {busy ? "Wird veröffentlicht …" : "Veröffentlichen"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
