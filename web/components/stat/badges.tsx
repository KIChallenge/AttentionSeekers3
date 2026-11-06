import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const CLASS: Record<string, { label: string; cls: string }> = {
  explained_plausible: { label: "erklärt – plausibel", cls: "bg-success/10 text-success" },
  explained_data_problem: { label: "erklärt – Datenproblem", cls: "bg-warning/10 text-warning" },
  unexplained: { label: "nicht erklärbar", cls: "bg-destructive/10 text-destructive" },
};

export function ClassificationBadge({ value }: { value: string }) {
  const c = CLASS[value] ?? { label: value, cls: "bg-secondary text-secondary-foreground" };
  return <Badge className={cn("shrink-0", c.cls)}>{c.label}</Badge>;
}

const STATUS: Record<string, { label: string; cls: string }> = {
  vorlaeufig: { label: "vorläufig", cls: "bg-secondary text-muted-foreground" },
  veroeffentlicht: { label: "veröffentlicht", cls: "bg-success/10 text-success" },
  published: { label: "veröffentlicht", cls: "bg-success/10 text-success" },
  done: { label: "fertig", cls: "bg-success/10 text-success" },
  running: { label: "läuft", cls: "bg-info/10 text-info" },
  failed: { label: "fehlgeschlagen", cls: "bg-destructive/10 text-destructive" },
  error: { label: "Fehler", cls: "bg-destructive/10 text-destructive" },
  proposed: { label: "vorgeschlagen", cls: "bg-warning/10 text-warning" },
  approved: { label: "freigegeben", cls: "bg-success/10 text-success" },
  rejected: { label: "abgelehnt", cls: "bg-destructive/10 text-destructive" },
  retired: { label: "außer Kraft", cls: "bg-secondary text-muted-foreground" },
  open: { label: "offen", cls: "bg-warning/10 text-warning" },
  offen: { label: "offen", cls: "bg-warning/10 text-warning" },
  executed: { label: "ausgeführt", cls: "bg-success/10 text-success" },
};

export function StatusBadge({ value, label }: { value: string | null | undefined; label?: string }) {
  const v = value ?? "";
  const s = STATUS[v] ?? { label: v || "–", cls: "bg-secondary text-secondary-foreground" };
  return <Badge className={cn("shrink-0", s.cls)}>{label ?? s.label}</Badge>;
}

export function Mono({ children, className, title }: { children: React.ReactNode; className?: string; title?: string }) {
  return (
    <span className={cn("font-mono text-xs tabular-nums", className)} title={title}>
      {children}
    </span>
  );
}
