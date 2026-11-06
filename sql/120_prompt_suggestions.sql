-- Example questions in „Fragen“, chosen by testing them with the live agent (06.11.2026): each one gives a clean answer
-- card with a fitting chart (line, ring, bars, pyramid) and a passed claim check. Two deliberately show the Rückfrage.
DELETE FROM ops.prompt_suggestion;
INSERT INTO ops.prompt_suggestion (text_de, role, sort) VALUES
  ('Zeitreihe der Beschäftigten nach Geschlecht', 'alle', 1),                                  -- 2 lines, 24 months, DQ markers
  ('Wie viele Männer und Frauen waren im Juli 2026 beschäftigt?', 'Jury', 2),                -- ring + KPIs
  ('Fluktuation je Wirtschaftszweig 2025', 'Jury', 3),                                        -- Rückfrage with three readings
  ('Beschäftigte nach Bundesland im Juli 2026', 'Reporting', 4),                              -- sorted bars
  ('Beschäftigte nach Altersgruppen im Juli 2026', 'Reporting', 5),                           -- ordered columns / line
  ('Beschäftigte nach Wirtschaftszweig im Juli 2026', 'Reporting', 6),                        -- 23 sections as bars
  ('Entwicklung der Beschäftigten in Tirol 2025', 'Reporting', 7),                            -- seasonal line
  ('Entwicklung der Alterspensionen von Männern und Frauen seit 2018', 'Reporting', 8),       -- pensions, 2 lines
  ('Fluktuationsrate nach Bundesland 2025', 'Qualitätssicherung', 9),                         -- rates per Bundesland
  ('Abgänge im Oktober und November 2025', 'Qualitätssicherung', 10),                         -- DQ-02 options on a copy
  ('Zeig mir den Qualitätsbericht 2025-03', 'Qualitätssicherung', 11),
  ('Was ist aus ÖNACE-Abschnitt J geworden?', 'Klassifikation', 12),                          -- transition graph
  ('Erkläre Gemeinde 62388', 'Klassifikation', 13),
  ('Alterspyramide im Juli 2026', 'Datenmanagement', 14),                                     -- Rückfrage, then pyramid
  ('Zeig mir alle Männer und Frauen, die im Juni 2026 gearbeitet haben', 'alle', 15);       -- free wording, agent
