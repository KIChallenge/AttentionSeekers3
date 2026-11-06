/** Response contracts of the StatAgent API (see docs/PRD.md and statagent/api/app.py). */

export type Health = {
  ok: boolean;
  db: { db: string; version: string; now: string } | null;
  llm: { configured: boolean; mode: string; mode_label: string; deployment: string | null };
  offline_ready?: boolean;
  /** name logged for questions when nobody is logged in (STATAGENT_FRAGEN_PERSON) */
  fragen_person?: string;
};

export type Overview = {
  stats: {
    deliveries: number;
    rows: number;
    files: number;
    runs_done: number;
    rules_approved: number;
    rules_proposed: number;
    findings: number;
    klass_entries: number;
    transitions: number;
  };
  series: { regelwerk: string; monat: string; wert: number; status: string }[];
};

export type RunRef = {
  delivery?: string;
  month?: string;
  rule_set?: string;
  run_id: number;
  checksum: string;
  finished_at?: string;
  status: string;
};

export type Profile = Record<string, number>;

export type Delivery = {
  month: string;
  file_name: string;
  rows: number;
  path: string;
  sha256: string;
  size_bytes: number;
  loaded_at: string;
  profile: Profile | null;
  runs: Record<string, RunRef>;
};

export type PackageFile = {
  path: string;
  area: string;
  format: string;
  size_bytes: number;
  sha256: string;
  encoding: string | null;
  units: number | null;
  loaded_at: string;
};

export type Run = {
  run_id: number;
  kind: string;
  delivery: string | null;
  rule_set: string | null;
  rules: string[] | null;
  started_at: string;
  finished_at: string | null;
  status: string;
  row_count: number | null;
  checksum: string | null;
  note: string | null;
  kind_label?: string;
  status_label?: string;
};

export type Finding = {
  finding_id?: number;
  run_id?: number;
  delivery?: string;
  check_id?: string;
  problem_id: string | null;
  level: string;
  description: string;
  extent: number | null;
  example_ids: string[] | null;
  evidence_sql: string | null;
  classification: "explained_plausible" | "explained_data_problem" | "unexplained" | string;
  measure: string | null;
  rule_id: string | null;
  inquiry_id: string | null;
};

export type Revision = {
  run_id?: number;
  month: string;
  delivery?: string;
  published: number | null;
  current: number | null;
  new_vvh: number | null;
  vanished_vvh: number | null;
  vanished_dq16: number | null;
  carried_total: number | null;
  carried_confirmed: number | null;
  main_cause: string | null;
};

export type RunMetrics = Record<string, number>;

export type RunDetail = {
  run: Run;
  metrics: RunMetrics | null;
  findings: Finding[];
  revisions: Revision[];
  report: { report_id: number; path: string; sha256: string; created_at: string } | null;
};

export type QbListItem = {
  month: string;
  rule_set: string;
  run_id: number;
  path: string;
  sha256: string;
  created_at: string;
  checksum: string;
  findings: number;
  unexplained: number;
  total: number;
  status: string;
};

export type QbDetail = {
  report: { report_id: number; kind: string; rule_set: string; month: string; run_id: number; path: string; content: string; sha256: string; created_at: string };
  run: Run;
  metrics: RunMetrics | null;
  findings: Finding[];
  revisions: Revision[];
};

export type Rule = {
  rule_id: string;
  problem_id: string | null;
  type: string;
  title: string;
  description: string;
  assumption: string | null;
  justification: string | null;
  action: string;
  parameters: Record<string, unknown> | null;
  rule_set: string;
  status: string;
  status_label?: string;
  created_by: string | null;
  created_at: string;
  approved_by: string | null;
  approved_at: string | null;
  hits?: { rule_id: string; rule_set: string; month: string; n: number }[];
};

export type Inquiry = {
  inquiry_id: string;
  delivery: string;
  problem_id: string;
  question: string;
  proposal: string | null;
  extent: number | null;
  example_ids: string[] | null;
  evidence_sql: string | null;
  status?: string;
  [k: string]: unknown;
};

export type Evidence = {
  rule_set: string;
  deliveries: { month: string; file: string; sha256: string }[];
  runs: { month: string; run_id: number; checksum: string; status: string; finished_at?: string }[];
  rules: { id: string; title: string; approved_by: string | null; approved_at: string | null; problem: string | null }[];
  klass_versions: string[];
  klass_run: { run_id: number; checksum: string } | null;
};

export type StatRow = { monat: string; wert: number; [k: string]: string | number | null };

export type StatResult = {
  tool?: string;
  params?: Record<string, unknown>;
  columns: string[];
  rows: StatRow[];
  sql: string;
  definition: string;
  evidence: Evidence;
  warnings: string[];
  numbers: number[];
  unit: string;
};

export type StatQuery = {
  regelwerk: string;
  monate: string[];
  dimensionen: string[];
  filter?: Record<string, string | string[]>;
  kennzahl: string;
};

export type ExampleRecords = {
  read: Record<string, unknown>[];
  delivered: Record<string, unknown>[];
  sql_read: string;
  sql_delivered: string;
};

export type Approval = {
  approval_id: number;
  object_type: string;
  object_id: string;
  decision: string;
  person: string;
  decided_at: string;
  comment: string | null;
};

export type CodeProposal = {
  proposal_id: string | number;
  instruction: string;
  path: string;
  sha256: string;
  status: string;
  content?: string;
  diff?: string;
  created_at?: string;
};

export type ProtocolEntry = {
  log_id: number;
  logged_at: string;
  object: string;
  change: string;
  instruction: string;
  approved_by: string;
  git_commit: string;
};

export type KlassSummary = {
  summary: { klassifikation: string; version: string; ebene: string; n: number; von: string | null; bis: string | null }[];
  transitions: { klassifikation: string; version_alt: string; version_neu: string; beziehung: string; n: number }[];
  mappings: {
    quelle: string;
    merkmal: string;
    quellwert: string;
    klassifikation: string;
    version: string;
    code: string;
    gueltig_von: string;
    gueltig_bis: string | null;
    regel_id: string | null;
    rule_status: string | null;
  }[];
  run: { run_id: number; checksum: string; finished_at: string } | null;
};

export type KlassEntry = {
  version: string;
  code: string;
  bezeichnung: string;
  ebene: string;
  uebergeordnet: string | null;
  gueltig_von: string | null;
  gueltig_bis: string | null;
  attribute: Record<string, unknown> | null;
};

export type KlassEdge = {
  version_alt: string;
  code_alt: string;
  version_neu: string;
  code_neu: string;
  beziehung: string;
  gueltig_ab: string | null;
  anteil: number | null;
  anmerkung: string | null;
};

export type KlassExplanation = {
  text: string;
  edges: KlassEdge[];
  nodes: { id: string; version: string; code: string; label: string }[];
};
