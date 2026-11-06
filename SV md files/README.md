# StatAgent – Startpaket

| Ordner / Datei | Inhalt |
|----------------|--------|
| `Aufgabenstellung_StatAgent.md` | die Aufgabenstellung: Prozess, fünf Schritte, Regeln, Abgabe, Bewertung |
| `Fachbeschreibung.md` | Satzaufbau, Klassifikationen, Zählregeln, Ergebnisformate |
| `lieferungen/` | 24 Monatslieferungen `lieferung_JJJJ-MM.csv.gz` (gepackte CSV, Semikolon, UTF-8) |
| `pensionen/` | aggregierte Lieferungen der Pensionsversicherungsträger zu Tabelle 12 und 13 der Jahresergebnisse, 2018–2025, je Träger und Jahr eine Excel-Datei in trägereigenem Format (siehe `pensionen/LIESMICH.txt`) |
| `klassifikationen/` | ÖNACE 2008, ÖNACE 2025, Bundesland, Qualifikation, Geschlecht; `oenace/` alle ÖNACE-Ebenen mit Umsteigern; `regionen/` Gemeinden, Bezirke und Bundesländer je Stand 2011–2026, dazu in `regionen/Änderungen/` die amtlichen Änderungslisten (Kennziffern, Zusammenlegungen, Teilungen, Bezirksänderungen) |
| `aenderungsauftraege.md` | die drei Änderungsaufträge für Freitag |
| `beispielbericht_2024-08.xlsx` | Monatsbericht August 2024 im Layout des Dachverbands, 13 Tabellen |
| `vorlagen/` | Vorlagen für Aggregations-Sheet, Ministeriums-Lieferung, Qualitätsbericht und Rückfrage |
| `docker-compose.yml`, `datenbank/` | lokale PostgreSQL-Datenbank, beim ersten Start mit allen Lieferungen befüllt |

## Datenbank starten

Voraussetzung: Docker (Docker Desktop oder Docker Engine mit Compose).

```
docker compose up -d
docker logs -f statagent-db      # wartet, bis "fertig" erscheint (ca. 2–4 Minuten)
```

Verbindung: Host `localhost`, Port `5432`, Datenbank, Benutzer und Passwort jeweils `statistik`. Ist Port 5432 belegt: `DB_PORT=5433 docker compose up -d` (Windows PowerShell: `$env:DB_PORT=5433; docker compose up -d`).

| Tabelle | Inhalt |
|---------|--------|
| `roh.lieferung` | alle Lieferungen untereinander, Spalte `lieferung` = Berichtsmonat (JJJJ-MM), alle Felder als Text; leere Felder sind NULL |
| `roh.ladeprotokoll` | geladene Dateien mit Zeilenzahl |
| `klassifikation.*` | die Klassifikationstabellen |

Alles Weitere – bereinigte Tabellen, Regeln, Ergebnisse, Protokolle – legt ihr selbst an.

Datenbank neu aufsetzen (löscht alle eigenen Tabellen): `docker compose down -v` und wieder `docker compose up -d`.

Die Datenbank läuft vollständig lokal und braucht nach dem ersten Herunterladen des Images kein Internet.

## Hinweise für die Umsetzung

- **Versionen.** Die Datenbank ist PostgreSQL 16 aus `docker-compose.yml`; wer Funktionen wie `range_agg` nutzt, braucht mindestens PostgreSQL 14. Für Python gilt die Version auf eurem Gerät (auf manchen Macs noch 3.9): Nennt in eurer Doku die Mindestversion, wenn euer Code neuere Syntax verwendet.
- **Python-Pakete.** `python3 -I` (isolierter Modus) ignoriert Pakete im Benutzerverzeichnis, etwa ein dort installiertes `psycopg2`. Startet euren eigenen Code ohne `-I` oder in einer virtuellen Umgebung mit den nötigen Paketen.
- **Lange Läufe.** Ein Gesamtlauf über alle Lieferungen kann dauern. Schreibt von Anfang an in eine Logdatei und startet Python ungepuffert (`python3 -u …`), damit der Fortschritt mit `tail -f` sichtbar ist.
- **Große Tabellen.** Die Lieferungen ergeben zusammen rund 10 Millionen Zeilen. Nach dem Laden `ANALYZE` ausführen, Abfragepläne mit `EXPLAIN` prüfen und statt `NOT IN` mit großen Mengen `NOT EXISTS` oder einen Join verwenden.