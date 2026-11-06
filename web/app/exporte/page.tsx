"use client";

import { Download04Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useState } from "react";
import { toast } from "sonner";
import { useApi } from "@/hooks/use-api";
import { useSseJob } from "@/hooks/use-sse-job";
import { ApiError, apiPost } from "@/lib/api";
import type { Rule } from "@/lib/types";
import { fmtBytes, fmtDateTime, shortHash, ruleSetLabel } from "@/lib/format";
import { useUser } from "@/components/shell/user-provider";
import { CopyButton } from "@/components/stat/code-block";
import { PageHeading, PageShell, Panel } from "@/components/stat/page-shell";
import { ProgressCard } from "@/components/stat/progress-card";
import { EmptyState, ErrorState, LoadingState } from "@/components/stat/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type ExportFile = {
  path: string;
  kind: string;
  size: number;
  sha256: string;
  modified: number;
  approved: { object_id: string; person: string; decided_at: string } | null;
};

export default function ExportsPage() {
  const { user } = useUser();
  const files = useApi<{ files: ExportFile[] }>("/api/exporte");
  const rules = useApi<{ rules: Rule[] }>("/api/regeln");
  const ministryRule = (rules.data?.rules ?? []).find((r) => r.action === "ministry_delivery");
  const ministryReady = ministryRule?.status === "approved";
  const sheet = useSseJob<Record<string, unknown>>();
  const ministry = useSseJob<Record<string, unknown>>();
  const [busyPath, setBusyPath] = useState<string | null>(null);
  const [ruleSet, setRuleSet] = useState("basis");
  const [confirmFile, setConfirmFile] = useState<ExportFile | null>(null);

  async function run(job: typeof sheet, path: string, label: string) {
    const r = await job.start(path);
    files.reload();                                   // always refresh the list – also after an error
    if (r) toast.success(`${label} erzeugt`);
  }

  // W-11: styled confirmation dialog instead of window.confirm – the person sees file, SHA-256 and their name
  function approve(f: ExportFile) {
    if (!user) return;
    setConfirmFile(f);
  }

  async function confirmApprove() {
    const f = confirmFile;
    if (!f || !user) return;
    setConfirmFile(null);
    setBusyPath(f.path);
    try {
      await apiPost("/api/exporte/freigeben", { path: f.path, person: user, comment: null });
      toast.success(`${f.path} freigegeben von ${user}`);
      files.reload();
    } catch (e) {
      toast.error("Freigabe abgelehnt", { description: e instanceof ApiError ? e.message : String(e) });
    } finally {
      setBusyPath(null);
    }
  }

  return (
    <PageShell wide>
      <PageHeading
        title="Exporte"
        description="Abgabedateien: Aggregations-Sheets, Open-Data-File, Ministeriums-Lieferung und Qualitätsberichte – jeweils mit SHA-256. Eine Lieferung nach außen braucht die Freigabe einer Person."
      />
      <div className="grid gap-4 md:grid-cols-2">
        <Panel title="Aggregations-Sheet + Open-Data-File" description="Erzeugt aus stat_beschaeftigte des gewählten Regelwerks.">
          <div className="flex flex-wrap items-center gap-2">
            {["basis", "auftraege"].map((r) => (
              <Button key={r} size="sm" variant={r === ruleSet ? "default" : "outline"} onClick={() => setRuleSet(r)}>
                {ruleSetLabel(r)}
              </Button>
            ))}
            <Button
              size="sm"
              className="ml-auto"
              disabled={sheet.status === "running"}
              onClick={() => run(sheet, `/api/exporte/aggregationen?regelwerk=${ruleSet}`, "Aggregations-Sheet")}
            >
              Erzeugen
            </Button>
          </div>
          <ProgressCard
            title="Aggregations-Sheet"
            status={sheet.status}
            steps={sheet.steps.map((s) => ({ step: s.detail ?? s.step, pct: s.pct }))}
            pct={sheet.pct}
            error={sheet.error}
          />
        </Panel>
        <Panel
          title="Ministeriums-Lieferung 07/2026"
          description="Änderungsauftrag 3: alle Personen mit mindestens 200 Tagen als Arbeiter (DV oder FD) in ÖNACE-Abschnitt C in den zwölf Monaten bis zum Berichtsmonat – je Tag die jüngste Lieferung. Datei ministerium_JJJJ-MM.csv (PERSON_ID;GESCHLECHT;GEBURTSJAHR;TAGE) nach der Vorlage in vorlagen/."
        >
          {!ministryReady && (
            <p className="text-xs text-warning">
              {ministryRule
                ? `Regel ${ministryRule.rule_id} ist noch nicht freigegeben – zuerst in Freigaben entscheiden.`
                : "Noch keine Regel: Änderungsauftrag 3 auf der Seite „Agent“ in Sprache erteilen, dann in Freigaben von einer Person freigeben lassen."}
            </p>
          )}
          <Button
            size="sm"
            className="w-fit"
            disabled={ministry.status === "running" || !ministryReady}
            onClick={() => run(ministry, "/api/exporte/ministerium", "Ministeriums-Lieferung")}
          >
            Erzeugen{ministryRule && ministryReady ? ` (Regel ${ministryRule.rule_id})` : ""}
          </Button>
          <ProgressCard
            title="Ministeriums-Lieferung"
            status={ministry.status}
            steps={ministry.steps.map((s) => ({ step: s.detail ?? s.step, pct: s.pct }))}
            pct={ministry.pct}
            error={ministry.error}
          />
          {(() => {
            const f = files.data?.files.find((x) => x.path.includes("ministerium_"));
            if (!f) return null;
            return (
              <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border px-3 py-2 text-xs">
                <span className="font-mono">{f.path}</span>
                <span className="text-muted-foreground">
                  {fmtBytes(f.size)} · {fmtDateTime(new Date(f.modified * 1000).toISOString())}
                </span>
                {f.approved ? (
                  <Badge className="bg-success/10 text-success">freigegeben von {f.approved.person}</Badge>
                ) : (
                  <Badge className="bg-warning/10 text-warning">wartet auf Freigabe (Tabelle unten)</Badge>
                )}
                <Button asChild variant="outline" size="xs" className="ml-auto">
                  <a href={`/api/exporte/datei?path=${encodeURIComponent(f.path)}`} download>
                    Herunterladen
                  </a>
                </Button>
              </div>
            );
          })()}
        </Panel>
      </div>
      <Panel title="Abgabedateien">
        {files.error ? (
          <ErrorState error={files.error} onRetry={files.reload} what="Exporte" />
        ) : !files.data ? (
          <LoadingState rows={6} />
        ) : files.data.files.length === 0 ? (
          <EmptyState title="Noch keine Dateien" />
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Datei</TableHead>
                  <TableHead className="text-xs">Art</TableHead>
                  <TableHead className="text-right text-xs">Größe</TableHead>
                  <TableHead className="text-xs">SHA-256</TableHead>
                  <TableHead className="text-xs">Stand</TableHead>
                  <TableHead className="text-xs">Freigabe</TableHead>
                  <TableHead className="text-xs">
                    <span className="sr-only">Herunterladen</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {files.data.files.map((f) => (
                  <TableRow key={f.path}>
                    <TableCell className="font-mono text-xs">{f.path}</TableCell>
                    <TableCell className="text-xs">{f.kind}</TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">{fmtBytes(f.size)}</TableCell>
                    <TableCell>
                      <span className="flex items-center gap-1 font-mono text-xs text-muted-foreground" title={f.sha256}>
                        {shortHash(f.sha256, 12)}
                        <CopyButton text={f.sha256} label="SHA-256 kopieren" />
                      </span>
                    </TableCell>
                    <TableCell className="text-xs whitespace-nowrap text-muted-foreground">{fmtDateTime(new Date(f.modified * 1000).toISOString())}</TableCell>
                    <TableCell className="text-xs whitespace-nowrap">
                      {f.approved ? (
                        <Badge className="bg-success/10 text-success" title={fmtDateTime(f.approved.decided_at)}>
                          {f.approved.person}
                        </Badge>
                      ) : (
                        <Button size="xs" variant="outline" disabled={!user || busyPath === f.path} onClick={() => approve(f)} title={user ? undefined : "Bitte anmelden"}>
                          Freigeben
                        </Button>
                      )}
                    </TableCell>
                    <TableCell>
                      <Button asChild variant="ghost" size="icon-xs" aria-label={`${f.path} herunterladen`}>
                        <a href={`/api/exporte/datei?path=${encodeURIComponent(f.path)}`} download>
                          <HugeiconsIcon icon={Download04Icon} strokeWidth={2} />
                        </a>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </Panel>
      <Dialog open={!!confirmFile} onOpenChange={(o) => !o && setConfirmFile(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Zur Lieferung freigeben?</DialogTitle>
            <DialogDescription>Die Freigabe wird mit Namen und Zeitpunkt protokolliert und kann nicht von einem Agenten erteilt werden.</DialogDescription>
          </DialogHeader>
          {confirmFile && (
            <div className="flex flex-col gap-2 text-sm">
              <span className="font-mono break-all">{confirmFile.path}</span>
              <span className="flex items-center gap-1 font-mono text-xs break-all text-muted-foreground">
                SHA-256 {confirmFile.sha256}
                <CopyButton text={confirmFile.sha256} label="SHA-256 kopieren" />
              </span>
              <span>
                Freigabe durch <span className="font-medium">{user}</span>
              </span>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmFile(null)}>
              Abbrechen
            </Button>
            <Button onClick={confirmApprove}>Als {user} freigeben</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageShell>
  );
}
