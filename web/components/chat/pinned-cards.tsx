"use client";

import { RefreshIcon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import { useState } from "react";
import { toast } from "sonner";
import { ApiError, streamSse } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import { type Pin, removePin, updatePin, usePins } from "@/lib/pins";
import { useUser } from "@/components/shell/user-provider";
import { SectionTitle } from "@/components/stat/page-shell";
import { Button } from "@/components/ui/button";
import { type AnswerCardData, AnswerCard } from "./answer-card";

/** Cards pinned from „Fragen“. A snapshot of the answer at pin time (run and checksum of that time) – „Aktualisieren“
 * asks the same question again with the same parameters and reading and replaces the snapshot (W-07). */
export function PinnedCards() {
  const pins = usePins();
  const { user } = useUser();
  const [busy, setBusy] = useState<string | null>(null);
  if (!pins.length) return null;

  async function refresh(p: Pin) {
    setBusy(p.id);
    let fresh: AnswerCardData | null = null;
    let problem: string | null = null;
    try {
      await streamSse(
        "/api/fragen",
        {
          question: p.question,
          user: user ?? null,
          conversation_id: `pin-${p.id}`,
          previous: p.card.params ?? null,
          ...(p.card.readings && Object.keys(p.card.readings).length ? { reading: p.card.readings } : {}),
        },
        ({ event, data }) => {
          const d = data as Record<string, unknown>;
          if (event === "card") fresh = d as unknown as AnswerCardData;
          else if (event === "abstention" || event === "error") problem = String(d.reason ?? d.message ?? "keine Antwort");
          else if (event === "clarification") problem = "Rückfrage nötig – bitte in „Fragen“ neu stellen";
        },
      );
      if (fresh) {
        updatePin(p.id, fresh);
        toast.success("Karte aktualisiert", { description: p.question });
      } else toast.error("Nicht aktualisiert", { description: problem ?? "keine Karte erhalten" });
    } catch (e) {
      toast.error("Nicht aktualisiert", { description: e instanceof ApiError ? e.message : String(e) });
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="flex flex-col gap-3" aria-label="Angeheftete Karten">
      <SectionTitle>Angeheftet aus „Fragen“</SectionTitle>
      <div className="grid gap-4 lg:grid-cols-2">
        {pins.map((p) => (
          <div key={p.id} className="flex flex-col gap-1">
            <span className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              „{p.question}“ · Stand {fmtDateTime(p.pinnedAt)}
              <Button size="xs" variant="outline" className="rounded-full" disabled={busy === p.id} onClick={() => refresh(p)}>
                <HugeiconsIcon icon={RefreshIcon} strokeWidth={2} data-icon="inline-start" />
                {busy === p.id ? "wird neu berechnet …" : "Aktualisieren"}
              </Button>
            </span>
            <AnswerCard card={p.card} question={p.question} pinnable={false} onUnpin={() => removePin(p.id)} />
          </div>
        ))}
      </div>
    </section>
  );
}
