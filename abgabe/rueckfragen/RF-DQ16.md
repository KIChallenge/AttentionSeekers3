# Rückfrage an die Fachabteilung

Team: AttentionSeekers3 · Nr.: RF-DQ16 · Datum: 06.11.2026

**Betroffene Lieferung(en):** lieferung_2024-08

**Was ist aufgefallen?** (DQ-16) Jeden Monat melden rund 200 Personen ein zweites, neues Verhältnis mit identischen Merkmalen zu einem bestehenden; diese Verhältnisse fehlen in der nächsten Lieferung vollständig. Handelt es sich um Doppelmeldungen, die nicht gezählt werden sollen?

**Beleg**

| Angabe | Wert |
| --- | --- |
| Anzahl betroffener Sätze | 207 |
| Zeitraum / ab welcher Lieferung | ab lieferung_2024-08 |
| betroffene Merkmale (Bundesland, ÖNACE, Qualifikation …) | neue VVH derselben Person mit identischen Merkmalen |
| Beispiel-IDs (VVH_ID, 3–5 Stück) | 65314, 67806, 76882, 116341, 159266 |

Abfrage, mit der das nachvollzogen werden kann:

```sql
SELECT vvh_id, person_id, begin_date, qual_raw, oenace_raw, bundesland_raw FROM store.month_record WHERE rule_set = 'basis' AND month = '2024-08' AND 'DQ-16' = ANY(problems)
```

**Unser Vorschlag zur Behandlung:** Bis zur Antwort wie geliefert zählen (wie im Beispielbericht), Verdachtsfälle im QB ausweisen und mit der nächsten Lieferung als Revisionsbedarf bestätigen; nach Antwort als Leseregel umsetzen.

**Frage an die Fachabteilung:** Jeden Monat melden rund 200 Personen ein zweites, neues Verhältnis mit identischen Merkmalen zu einem bestehenden; diese Verhältnisse fehlen in der nächsten Lieferung vollständig. Handelt es sich um Doppelmeldungen, die nicht gezählt werden sollen?

---
*Antwort der Fachabteilung (wird von den Mentoren ausgefüllt):* 
