"use client";

import { Alert02Icon, InformationCircleIcon, Refresh01Icon } from "@hugeicons/core-free-icons";
import { HugeiconsIcon } from "@hugeicons/react";
import type { ReactNode } from "react";
import type { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";
import { FixLinks } from "./fix-links";

export function LoadingState({ label = "Wird geladen …", rows = 3, className }: { label?: string; rows?: number; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-2", className)} role="status" aria-live="polite">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Spinner className="size-3.5" />
        {label}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        // biome-ignore lint/suspicious/noArrayIndexKey: static skeleton
        <Skeleton key={i} className="h-8 w-full rounded-lg" />
      ))}
    </div>
  );
}

export function EmptyState({ title, description, action }: { title: string; description?: ReactNode; action?: ReactNode }) {
  return (
    <Empty className="rounded-2xl border border-dashed border-border py-10">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <HugeiconsIcon icon={InformationCircleIcon} strokeWidth={2} />
        </EmptyMedia>
        <EmptyTitle className="text-sm">{title}</EmptyTitle>
        {description && <EmptyDescription className="text-xs">{description}</EmptyDescription>}
      </EmptyHeader>
      {action}
    </Empty>
  );
}

/** Error / not-yet-available state. 404 = endpoint still being built. Never shows invented data. */
export function ErrorState({ error, onRetry, what }: { error: ApiError; onRetry?: () => void; what?: string }) {
  if (error.notAvailable)
    return (
      <EmptyState
        title="noch nicht verfügbar"
        description={`${what ? `${what}: ` : ""}Die Schnittstelle wird im Backend gerade gebaut. Es werden keine Ersatzwerte angezeigt.`}
        action={
          onRetry && (
            <Button variant="outline" size="sm" onClick={onRetry}>
              <HugeiconsIcon icon={Refresh01Icon} strokeWidth={2} data-icon="inline-start" />
              Erneut prüfen
            </Button>
          )
        }
      />
    );
  return (
    <div role="alert" className="flex items-start gap-3 rounded-2xl border border-destructive/30 bg-destructive/5 p-4 text-sm">
      <HugeiconsIcon icon={Alert02Icon} strokeWidth={2} className="mt-0.5 size-4 shrink-0 text-destructive" />
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="font-medium text-destructive">{what ? `${what} konnte nicht geladen werden` : "Fehler"}</span>
        <span className="text-muted-foreground">{error.message}</span>
        <FixLinks message={error.message} className="mt-1 flex flex-wrap gap-1.5" />
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Erneut versuchen
        </Button>
      )}
    </div>
  );
}

const ABSTENTION: Record<string, string> = {
  "nicht vorhanden": "Diese Zahl gibt es im Bestand nicht.",
  "nicht geliefert": "Die Daten wurden nicht geliefert.",
  mehrdeutig: "Die Frage ist mehrdeutig – bitte präzisieren.",
  "nicht prüfbar": "Die Prüfung selbst ist fehlgeschlagen – es wird keine Zahl genannt.",
  "nicht verfügbar": "Dieses Merkmal ist in den Lieferungen nicht enthalten.",
  "außerhalb des Datenbestands": "Der Agent beantwortet nur Fragen zu den gelieferten Daten – kein Allgemeinwissen.",
};

/** Abstention: the system deliberately says no number (proven absence or failed check). */
export function AbstentionState({ kind, reason }: { kind?: string; reason: string }) {
  return (
    <div role="status" className="flex items-start gap-3 rounded-2xl border border-warning/30 bg-warning/5 p-4 text-sm">
      <HugeiconsIcon icon={InformationCircleIcon} strokeWidth={2} className="mt-0.5 size-4 shrink-0 text-warning" />
      <div className="flex min-w-0 flex-col gap-1">
        <span className="font-medium text-warning">{kind ? kind.charAt(0).toUpperCase() + kind.slice(1) : "Keine Zahl"}</span>
        <span>{reason}</span>
        {kind && ABSTENTION[kind] && <span className="text-xs text-muted-foreground">{ABSTENTION[kind]}</span>}
        {kind !== "außerhalb des Datenbestands" && <FixLinks message={reason} className="mt-1 flex flex-wrap gap-1.5" />}
      </div>
    </div>
  );
}
