# Rückfrage an die Fachabteilung

Team: AttentionSeekers3 · Nr.: RF-DQ04 · Datum: 06.11.2026

**Betroffene Lieferung(en):** lieferung_2025-03

**Was ist aufgefallen?** (DQ-04) In der Lieferung 2025-03 fehlen alle freien Dienstverträge (ArbeiterFD, AngestellteFD), im Folgemonat sind sie wieder da. Wurden sie technisch nicht mitgeliefert?

**Beleg**

| Angabe | Wert |
| --- | --- |
| Anzahl betroffener Sätze | 1.470 |
| Zeitraum / ab welcher Lieferung | ab lieferung_2025-03 |
| betroffene Merkmale (Bundesland, ÖNACE, Qualifikation …) | Qualifikation ArbeiterFD, AngestellteFD |
| Beispiel-IDs (VVH_ID, 3–5 Stück) | 448, 1054, 1264, 1289, 2247 |

Abfrage, mit der das nachvollzogen werden kann:

```sql
SELECT DISTINCT p.vvh_id FROM store.segment p WHERE p.delivery = '2025-02' AND p.qual LIKE '%FD' AND p.effective_end IS NULL
  AND NOT ('DQ-16' = ANY(p.problems)) AND NOT EXISTS (SELECT 1 FROM store.segment c WHERE c.delivery = '2025-03' AND c.vvh_id = p.vvh_id)
```

**Unser Vorschlag zur Behandlung:** Offene FD-Verhältnisse aus 2025-02 fortschreiben (Regel R-DQ04); Revision im QB 2025-04.

**Frage an die Fachabteilung:** In der Lieferung 2025-03 fehlen alle freien Dienstverträge (ArbeiterFD, AngestellteFD), im Folgemonat sind sie wieder da. Wurden sie technisch nicht mitgeliefert?

---
*Antwort der Fachabteilung (wird von den Mentoren ausgefüllt):* 
