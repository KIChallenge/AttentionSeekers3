-- Phase 3b – synthetic deliveries and models (schema synth, registry ops.model). Never mixed with delivered data:
-- nothing here is read by the production runs (statagent/qa/run.py) or written to stat_*.
CREATE SCHEMA IF NOT EXISTS synth;

CREATE TABLE IF NOT EXISTS synth.run (
  synth_run         bigint NOT NULL,          -- ops.run (kind 'synth')
  seed              integer NOT NULL,
  split             text NOT NULL CHECK (split IN ('train', 'calibration', 'test')),
  scale             numeric NOT NULL,
  months            integer NOT NULL,
  checksum          text NOT NULL,            -- generator output (seed → same checksum)
  calibration_hash  text NOT NULL,
  PRIMARY KEY (synth_run, seed)
);

CREATE TABLE IF NOT EXISTS synth.label (
  synth_run       bigint NOT NULL,
  seed            integer NOT NULL,
  delivery_index  integer NOT NULL,           -- 0 = synthetic delivery for 2024-08, …
  problem_id      text NOT NULL,
  PRIMARY KEY (synth_run, seed, delivery_index, problem_id)
);

CREATE TABLE IF NOT EXISTS ops.model (
  model_id    bigserial PRIMARY KEY,
  kind        text NOT NULL CHECK (kind IN ('corridor', 'detector')),
  version     text NOT NULL,
  trained_at  timestamptz NOT NULL DEFAULT now(),
  data_hash   text NOT NULL,
  model_hash  text NOT NULL,
  metrics     jsonb NOT NULL,
  seed        integer NOT NULL,
  note        text,
  synth_run   bigint
);

-- Predictions on the real deliveries, labelled "Modell": corridor per series, detector probability per problem.
CREATE TABLE IF NOT EXISTS synth.prediction (
  model_id     bigint NOT NULL REFERENCES ops.model,
  delivery     text NOT NULL,
  series       text NOT NULL,               -- corridor: series name; detector: problem ID
  expected     numeric, lower numeric, upper numeric, actual numeric,
  flag         boolean NOT NULL,
  probability  numeric,
  features     jsonb,
  PRIMARY KEY (model_id, delivery, series)
);
