# Rückfrage an die Fachabteilung

Team: AttentionSeekers3 · Nr.: RF-DQ02 · Datum: 06.11.2026

**Betroffene Lieferung(en):** lieferung_2025-10

**Was ist aufgefallen?** (DQ-02) Die Lieferung 2025-10 enthält rund 20 % weniger Sätze als die Nachbarlieferungen; der Ausfall ist über alle Merkmale gleich verteilt. Ist die Lieferung unvollständig, und gibt es eine Nachlieferung?

**Beleg**

| Angabe | Wert |
| --- | --- |
| Anzahl betroffener Sätze | 77.510 |
| Zeitraum / ab welcher Lieferung | ab lieferung_2025-10 |
| betroffene Merkmale (Bundesland, ÖNACE, Qualifikation …) | alle (gleich verteilt) |
| Beispiel-IDs (VVH_ID, 3–5 Stück) | 34, 79, 95, 122, 133 |

Abfrage, mit der das nachvollzogen werden kann:

```sql
SELECT p.vvh_id FROM store.segment p WHERE p.delivery = '2025-09' AND p.counted AND p.effective_end IS NULL
  AND NOT ('DQ-16' = ANY(p.problems))
  AND NOT EXISTS (SELECT 1 FROM store.segment c WHERE c.delivery = '2025-10' AND c.vvh_id = p.vvh_id)
```

**Unser Vorschlag zur Behandlung:** Zuvor offene, jetzt fehlende Verhältnisse mit den Merkmalen der Vorlieferung fortschreiben (Regel R-DQ02); veröffentlichte Zahl als Annahme kennzeichnen, Revision mit der Lieferung 2025-11.

**Frage an die Fachabteilung:** Die Lieferung 2025-10 enthält rund 20 % weniger Sätze als die Nachbarlieferungen; der Ausfall ist über alle Merkmale gleich verteilt. Ist die Lieferung unvollständig, und gibt es eine Nachlieferung?

---
*Antwort der Fachabteilung (wird von den Mentoren ausgefüllt):* 
