const nf = new Intl.NumberFormat("de-DE");
const nf1 = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 2 });

/** German number formatting (392.236). Returns „–“ for missing values – never a guess. */
export function fmt(n: number | null | undefined, digits?: number): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  if (digits !== undefined)
    return new Intl.NumberFormat("de-DE", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(n);
  return Number.isInteger(n) ? nf.format(n) : nf1.format(n);
}

export function fmtSigned(n: number | null | undefined): string {
  if (n === null || n === undefined) return "–";
  return (n > 0 ? "+" : "") + fmt(n);
}

export function fmtBytes(n: number | null | undefined): string {
  if (n === null || n === undefined) return "–";
  if (n < 1024) return `${fmt(n)} B`;
  if (n < 1024 * 1024) return `${fmt(n / 1024, 1)} KB`;
  return `${fmt(n / 1024 / 1024, 1)} MB`;
}

export function fmtDateTime(s: string | null | undefined): string {
  if (!s) return "–";
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function fmtDate(s: string | null | undefined): string {
  if (!s) return "–";
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" });
}

const MONTHS = ["Jän.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sep.", "Okt.", "Nov.", "Dez."];
/** "2025-03" → "März 2025" */
export function fmtMonth(m: string | null | undefined, short = false): string {
  if (!m) return "–";
  const [y, mm] = m.split("-");
  const i = Number(mm) - 1;
  if (!y || Number.isNaN(i) || i < 0 || i > 11) return m;
  return short ? `${MONTHS[i]} ${y.slice(2)}` : `${MONTHS[i]} ${y}`;
}

export function shortHash(h: string | null | undefined, n = 12): string {
  if (!h) return "–";
  return h.length > n ? `${h.slice(0, n)}…` : h;
}

/** Rule sets as users see them: the stored values stay `basis` / `auftraege` (DB, URL, API). */
export const RULE_SET_LABELS: Record<string, string> = { basis: "Basis", auftraege: "Aufträge" };
export function ruleSetLabel(v: string | null | undefined): string {
  return v ? (RULE_SET_LABELS[v] ?? v) : "–";
}
