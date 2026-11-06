/** Contract of GET /api/modelle (Phase 3b – synthetic data and prediction models). */

export type DetectorMetric = {
  n: number;
  tp: number;
  fp: number;
  fn: number;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  positives: number;
};

export type Model = {
  model_id: number;
  kind: "corridor" | "detector" | string;
  version: string;
  trained_at: string;
  data_hash: string;
  model_hash: string;
  metrics: {
    // detector
    synthetic_test?: Record<string, DetectorMetric>;
    real_24?: Record<string, DetectorMetric>;
    // corridor
    nominal_coverage?: number;
    synthetic_test_coverage?: number;
    synthetic_test_points?: number;
    synthetic_detection?: Record<string, { found: number; planted: number }>;
    real_flags?: { series: string; delivery: string; expected: number; lower: number; upper: number; actual: number; flag: boolean }[];
    [k: string]: unknown;
  };
  seed: number;
  note: string | null;
  synth_run: number | null;
};

export type Prediction = {
  model_id: number;
  delivery: string;
  series: string;
  expected: number | null;
  lower: number | null;
  upper: number | null;
  actual: number | null;
  flag: boolean;
  probability: number | null;
  features: Record<string, number> | null;
};

export type SynthRun = { seed: number; split: string; scale: number; months: number; checksum: string; calibration_hash: string };

export type ModelsResponse = {
  banner: string;
  models: Model[];
  predictions: Prediction[];
  synthetic_runs: SynthRun[];
  limits: string[];
};

export const SERIES_LABELS: Record<string, string> = {
  total: "Insgesamt",
  A: "ÖNACE-Abschnitt A",
  C: "ÖNACE-Abschnitt C",
  F: "ÖNACE-Abschnitt F",
  I: "ÖNACE-Abschnitt I",
  Tirol: "Bundesland Tirol",
  FD: "Freie Dienstverträge (FD)",
};
