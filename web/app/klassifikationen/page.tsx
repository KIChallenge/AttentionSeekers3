"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useApi } from "@/hooks/use-api";
import { fmt, fmtDate, shortHash } from "@/lib/format";
import type { KlassEntry, KlassExplanation, KlassSummary } from "@/lib/types";
import { cn } from "@/lib/utils";
import { StatusBadge } from "@/components/stat/badges";
import { PageHeading, PageShell, Panel } from "@/components/stat/page-shell";
import { EmptyState, ErrorState, LoadingState } from "@/components/stat/states";
import { TransitionGraph } from "@/components/stat/transition-graph";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

const KLASS = [
  { id: "region", label: "Region", table: "klass_region" },
  { id: "oenace", label: "ÖNACE", table: "klass_oenace" },
  { id: "geschlecht", label: "Geschlecht", table: "klass_geschlecht" },
  { id: "qualifikation", label: "Qualifikation", table: "klass_qualifikation" },
  { id: "alter", label: "Alter", table: "klass_alter" },
];
const ALL = "__alle";

export default function Page() {
  return (
    <Suspense fallback={<PageShell><LoadingState /></PageShell>}>
      <ClassificationsPage />
    </Suspense>
  );
}

function ClassificationsPage() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const klass = params.get("klass") ?? "oenace";
  const code = params.get("code");
  const codeVersion = params.get("cv");
  const summary = useApi<KlassSummary>("/api/klassifikationen");
  const table = KLASS.find((k) => k.id === klass)?.table ?? "";
  const versions = useMemo(
    () => [...new Set((summary.data?.summary ?? []).filter((s) => s.klassifikation === table).map((s) => s.version))],
    [summary.data, table],
  );
  const [version, setVersion] = useState<string>(ALL);
  const [level, setLevel] = useState<string>(ALL);
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(q), 250);
    return () => clearTimeout(t);
  }, [q]);
  useEffect(() => {
    setLevel(ALL);
    setVersion(klass === "oenace" ? "2025" : ALL);
  }, [klass]);
  const levels = useMemo(
    () => (summary.data?.summary ?? []).filter((s) => s.klassifikation === table && (version === ALL || s.version === version)),
    [summary.data, table, version],
  );
  const qs = new URLSearchParams();
  if (version !== ALL) qs.set("version", version);
  if (level !== ALL) qs.set("ebene", level);
  if (debounced) qs.set("q", debounced);
  const entries = useApi<{ entries: KlassEntry[] }>(`/api/klassifikationen/${klass}?${qs.toString()}`);

  const set = (patch: Record<string, string | null>) => {
    const p = new URLSearchParams(params.toString());
    for (const [k, v] of Object.entries(patch)) v === null ? p.delete(k) : p.set(k, v);
    router.replace(`${pathname}?${p.toString()}`, { scroll: false });
  };

  return (
    <PageShell wide>
      <PageHeading
        title="Klassifikationen"
        description="Alle Klassifikationen mit Versionen, Ebenen, Gültigkeit und Übergängen (klass_*, klass_uebergang). Jede Erklärung wird deterministisch aus den Klassifikationsdateien erzeugt."
      />
      {summary.data?.run && (
        <p className="-mt-3 text-xs text-muted-foreground">
          Klassifikationslauf {summary.data.run.run_id} · Prüfsumme <span className="font-mono">{shortHash(summary.data.run.checksum, 16)}</span> ·{" "}
          {fmt(summary.data.summary.reduce((s, x) => s + x.n, 0))} Einträge · {fmt(summary.data.transitions.reduce((s, x) => s + x.n, 0))} Übergänge
        </p>
      )}
      <Tabs defaultValue="browser" className="gap-4">
        <TabsList className="bg-muted">
          <TabsTrigger value="browser">Codes</TabsTrigger>
          <TabsTrigger value="zuordnungen">Quellzuordnungen</TabsTrigger>
          <TabsTrigger value="uebergaenge">Übergänge</TabsTrigger>
        </TabsList>
        <TabsContent value="browser" className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-2">
            <ToggleGroup type="single" value={klass} onValueChange={(v) => v && set({ klass: v, code: null, cv: null })} variant="outline" size="sm" aria-label="Klassifikation">
              {KLASS.map((k) => (
                <ToggleGroupItem key={k.id} value={k.id} className="px-3">
                  {k.label}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
            {versions.length > 1 && (
              <Select value={version} onValueChange={(v) => { setVersion(v); setLevel(ALL); }}>
                <SelectTrigger size="sm" className="w-48" aria-label="Version">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>alle Versionen</SelectItem>
                  {versions.map((v) => (
                    <SelectItem key={v} value={v}>
                      {v}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {levels.length > 1 && (
              <Select value={level} onValueChange={setLevel}>
                <SelectTrigger size="sm" className="w-44" aria-label="Ebene">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>alle Ebenen</SelectItem>
                  {[...new Set(levels.map((l) => l.ebene))].map((l) => (
                    <SelectItem key={l} value={l}>
                      {l}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Code oder Bezeichnung …" className="h-8 w-60" aria-label="Suche" />
          </div>
          <div className="grid gap-4 xl:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
            <Panel title={entries.data ? `${fmt(entries.data.entries.length)} Einträge` : "Einträge"}>
              {entries.error ? (
                <ErrorState error={entries.error} onRetry={entries.reload} what="Einträge" />
              ) : !entries.data ? (
                <LoadingState rows={8} />
              ) : entries.data.entries.length === 0 ? (
                <EmptyState title="Keine Treffer" />
              ) : (
                <div className="max-h-[38rem] overflow-auto rounded-xl border border-border">
                  <Table>
                    <TableHeader className="sticky top-0 bg-card">
                      <TableRow>
                        <TableHead className="text-xs">Code</TableHead>
                        <TableHead className="text-xs">Bezeichnung</TableHead>
                        <TableHead className="text-xs">Ebene</TableHead>
                        <TableHead className="text-xs">Version</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {entries.data.entries.map((e) => {
                        const active = e.code === code && (codeVersion ?? e.version) === e.version;
                        return (
                          <TableRow
                            key={`${e.version}|${e.code}|${e.ebene}`}
                            tabIndex={0}
                            className={cn("cursor-pointer", active && "bg-sidebar-accent")}
                            onClick={() => set({ code: e.code, cv: e.version })}
                            onKeyDown={(ev) => ev.key === "Enter" && set({ code: e.code, cv: e.version })}
                          >
                            <TableCell className="font-mono text-xs font-medium">{e.code}</TableCell>
                            <TableCell className="text-xs">
                              {e.bezeichnung}
                              {e.gueltig_bis && <span className="ml-1 text-muted-foreground">(bis {fmtDate(e.gueltig_bis)})</span>}
                            </TableCell>
                            <TableCell className="text-xs text-muted-foreground">{e.ebene}</TableCell>
                            <TableCell className="text-xs whitespace-nowrap text-muted-foreground">{e.version}</TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </Panel>
            {code ? (
              <Explanation key={`${klass}|${code}|${codeVersion}`} klass={klass} code={code} version={codeVersion} onPick={(c, v) => set({ code: c, cv: v })} />
            ) : (
              <EmptyState title="Code auswählen" description="Erklärung und Übergangsgraph erscheinen hier. Beispiele: ÖNACE J (2008), Region 62388, Region 324." />
            )}
          </div>
        </TabsContent>
        <TabsContent value="zuordnungen">
          <Panel
            title="Quellzuordnungen (ZVD-Monatslieferung → Klassifikation)"
            description="Nur Zuordnungen ohne Regel oder mit freigegebener Regel werden gezählt (quellzuordnung_wirksam)."
          >
            {summary.data ? (
              <div className="overflow-x-auto rounded-xl border border-border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Merkmal</TableHead>
                      <TableHead className="text-xs">Quellwert</TableHead>
                      <TableHead className="text-xs">Klassifikation</TableHead>
                      <TableHead className="text-xs">Code</TableHead>
                      <TableHead className="text-xs">gültig</TableHead>
                      <TableHead className="text-xs">Regel</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {summary.data.mappings.map((m, i) => (
                      // biome-ignore lint/suspicious/noArrayIndexKey: mapping rows have no id
                      <TableRow key={i}>
                        <TableCell className="font-mono text-xs">{m.merkmal}</TableCell>
                        <TableCell className="font-mono text-xs">{m.quellwert === "" ? <span className="text-muted-foreground">leer</span> : m.quellwert}</TableCell>
                        <TableCell className="text-xs">
                          {m.klassifikation} {m.version}
                        </TableCell>
                        <TableCell className="font-mono text-xs">{m.code}</TableCell>
                        <TableCell className="text-xs whitespace-nowrap text-muted-foreground">
                          {fmtDate(m.gueltig_von)} – {m.gueltig_bis ? fmtDate(m.gueltig_bis) : "offen"}
                        </TableCell>
                        <TableCell className="text-xs">
                          {m.regel_id ? (
                            <span className="flex items-center gap-1.5">
                              <span className="font-mono">{m.regel_id}</span>
                              <StatusBadge value={m.rule_status} />
                            </span>
                          ) : (
                            "–"
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <LoadingState />
            )}
          </Panel>
        </TabsContent>
        <TabsContent value="uebergaenge">
          <Panel title="Übergänge je Versionswechsel und Beziehungstyp">
            {summary.data ? (
              <div className="overflow-x-auto rounded-xl border border-border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Klassifikation</TableHead>
                      <TableHead className="text-xs">von</TableHead>
                      <TableHead className="text-xs">nach</TableHead>
                      <TableHead className="text-xs">Beziehung</TableHead>
                      <TableHead className="text-right text-xs">Anzahl</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {summary.data.transitions.map((t, i) => (
                      // biome-ignore lint/suspicious/noArrayIndexKey: summary rows
                      <TableRow key={i}>
                        <TableCell className="text-xs">{t.klassifikation}</TableCell>
                        <TableCell className="text-xs">{t.version_alt}</TableCell>
                        <TableCell className="text-xs">{t.version_neu}</TableCell>
                        <TableCell className="font-mono text-xs">{t.beziehung}</TableCell>
                        <TableCell className="text-right font-mono text-xs tabular-nums">{fmt(t.n)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : (
              <LoadingState />
            )}
          </Panel>
        </TabsContent>
      </Tabs>
    </PageShell>
  );
}

function Explanation({ klass, code, version, onPick }: { klass: string; code: string; version: string | null; onPick: (code: string, version: string) => void }) {
  const qs = version && version !== "-" ? `?version=${encodeURIComponent(version)}` : "";
  const ex = useApi<KlassExplanation>(`/api/klassifikationen/${klass}/${encodeURIComponent(code)}/erklaerung${qs}`);
  return (
    <Panel title={`Erklärung ${code}${version && version !== "-" ? ` · ${version}` : ""}`} description="Deterministisch aus den Klassifikationsdateien – kein Sprachmodell.">
      {ex.error ? (
        <ErrorState error={ex.error} what="Erklärung" />
      ) : !ex.data ? (
        <LoadingState rows={4} />
      ) : (
        <>
          <pre className="max-h-72 overflow-auto rounded-xl border border-border bg-muted px-3 py-2 font-sans text-xs/5 whitespace-pre-wrap">{ex.data.text}</pre>
          {ex.data.edges.length > 0 ? (
            <TransitionGraph explanation={ex.data} focus={`${version ?? ""}|${code}`} onPick={onPick} />
          ) : (
            <p className="text-xs text-muted-foreground">Keine Übergänge für diesen Code.</p>
          )}
        </>
      )}
    </Panel>
  );
}
