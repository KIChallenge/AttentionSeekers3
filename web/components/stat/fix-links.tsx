"use client";

import { ArrowRight01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

type Fix = { href: string; label: string };

/**
 * Turns an error / abstention text into links to the place where it can be fixed
 * (e.g. „R-DQ02 … nicht freigegeben“ → Freigaben, „zuerst die Monatsläufe starten“ → Läufe).
 * Pure text matching on the API message – no guessing of numbers.
 */
export function fixesFor(message: string | null | undefined): Fix[] {
  if (!message) return [];
  const m = message;
  const out: Fix[] = [];
  const seen = new Set<string>();
  const add = (href: string, label: string) => {
    if (!seen.has(href)) {
      seen.add(href);
      out.push({ href, label });
    }
  };
  for (const id of m.match(/\bR-(?:DQ|A)\d+\b/g) ?? []) add(`/freigaben?regel=${id}`, `${id} in Freigaben entscheiden`);
  if (/\bC-\d{3,}\b/.test(m)) add("/freigaben", "Codevorschlag in Freigaben prüfen");
  if (/nicht (von einer Person )?freigegeben|Freigabe (fehlt|durch eine Person|braucht)|wartet auf Freigabe|noch nicht entschieden/i.test(m))
    add("/freigaben", "Zu den offenen Freigaben");
  if (/Monatsl(a|ä)uf|Lauf .*starten|noch keine Ergebnisse|nicht gerechnet|kein Ergebnis/i.test(m)) add("/laeufe", "Monatslauf starten (Läufe)");
  if (/anderer Auftrag/i.test(m)) add("/laeufe", "Laufende Aufträge ansehen");
  if (/Klassifikation|ÖNACE|Code .* unbekannt|nicht zuordenbar/i.test(m)) add("/klassifikationen", "Klassifikationen ansehen");
  if (/Regelwerk „?(auftraege|Aufträge)|Änderungsauftrag|Auftrag [123]|Setze die freigegebenen/i.test(m)) add("/agent", "Zum Agenten: Aufträge umsetzen");
  if (/Name einer Person|anmelden|angemeldet/i.test(m)) add("#anmelden", "Links unten mit Namen anmelden");
  if (/veröffentlich/i.test(m)) add("/freigaben", "Veröffentlichung in Freigaben");
  if (/Backend nicht erreichbar/i.test(m)) add("#backend", "Backend starten: .venv\\Scripts\\python.exe -m statagent web");
  return out;
}

export function FixLinks({ message, className }: { message: string | null | undefined; className?: string }) {
  const fixes = fixesFor(message);
  if (!fixes.length) return null;
  return (
    <div className={className ?? "flex flex-wrap gap-1.5"}>
      {fixes.map((f) =>
        f.href.startsWith("#") ? (
          <span key={f.href} className="rounded-full border border-border px-2 py-0.5 text-xs text-muted-foreground">
            {f.label}
          </span>
        ) : (
          <Button key={f.href} asChild size="xs" variant="outline" className="rounded-full">
            <Link href={f.href}>
              {f.label}
              <HugeiconsIcon icon={ArrowRight01Icon} strokeWidth={2} data-icon="inline-end" />
            </Link>
          </Button>
        ),
      )}
    </div>
  );
}
