# Prüfbericht Pensionsstatistik 2018–2025

Lauf 84 · Prüfsumme `194af349a90b5c5f6d8f4f9de8b2529d` · 28 Dateien · 1276 gelesene Zellen · 2092 Zeilen in `stat_pensionen` · 378 Summenprüfungen (gelieferte Summen = Summe der Teile), 0 Abweichungen

## 1 Formate (erkannt am Kopf, nicht an Jahr oder Position – PEN-01/02)

| Datei | Format |
| --- | --- |
| pensionen/2018/PVA_Jahresmeldung_2018.xlsx | pva_two_row |
| pensionen/2018/SVA_PV_2018.xlsx | code_columns |
| pensionen/2018/SVB Pensionen 2018.xlsx | code_columns |
| pensionen/2018/VAEB_Pensionen_2018.xlsx | blocks |
| pensionen/2018/VAN_Pensionsstand_2018.xlsx | long_van |
| pensionen/2019/PVA_Jahresmeldung_2019.xlsx | pva_two_row |
| pensionen/2019/SVA_PV_2019.xlsx | code_columns |
| pensionen/2019/SVB Pensionen 2019.xlsx | code_columns |
| pensionen/2019/VAEB_Pensionen_2019.xlsx | blocks |
| pensionen/2019/VAN_Pensionsstand_2019.xlsx | long_van |
| pensionen/2020/BVAEB_Pensionen_2020.xlsx | blocks |
| pensionen/2020/PVA_Jahresmeldung_2020.xlsx | pva_two_row |
| pensionen/2020/svs_pensionen_2020.xlsx | long_svs |
| pensionen/2021/BVAEB_Pensionen_2021.xlsx | blocks |
| pensionen/2021/PVA_Jahresmeldung_2021.xlsx | pva_two_row |
| pensionen/2021/svs_pensionen_2021.xlsx | long_svs |
| pensionen/2022/BVAEB_Pensionen_2022.xlsx | blocks |
| pensionen/2022/PVA_Jahresmeldung_2022.xlsx | pva_one_row |
| pensionen/2022/svs_pensionen_2022.xlsx | long_svs |
| pensionen/2023/BVAEB_Pensionen_2023.xlsx | blocks |
| pensionen/2023/PVA_Jahresmeldung_2023.xlsx | pva_one_row |
| pensionen/2023/svs_pensionen_2023.xlsx | long_svs |
| pensionen/2024/BVAEB_Pensionen_2024.xlsx | blocks |
| pensionen/2024/PVA_Jahresmeldung_2024.xlsx | pva_one_row |
| pensionen/2024/svs_pensionen_2024.xlsx | long_svs |
| pensionen/2025/BVAEB_Pensionen_2025.xlsx | blocks |
| pensionen/2025/PVA_Jahresmeldung_2025.xlsx | pva_one_row |
| pensionen/2025/svs_pensionen_2025.xlsx | long_svs |

Zahlen als Text mit Tausenderpunkt (VAEB/BVAEB, z. B. „18.228“) als ganze Zahlen gelesen (PEN-03). VAN meldet keine vorzeitigen Alterspensionen: Status „nicht gemeldet“, nicht 0 (PEN-04). Geschlecht in 7 Schreibweisen über die Quellzuordnung (PEN-08).

## 2 Zeitreihenbruch 2020 (PEN-06, RD-05)

SVA + SVB + VAN → SVS, VAEB (+ BVA) → BVAEB (klass_uebergang n:1, gültig ab 01.01.2020). Träger vor und nach 2020 sind nicht direkt vergleichbar; vergleichbar sind PV insgesamt, PV der Unselbständigen und PV der Selbständigen. Das Notariat ist ab 2020 kein eigener Bereich.

## 3 Sprünge > 25 % gegenüber dem Vorjahr

| Jahr | Träger/Bereich | Art | Geschlecht | Vorjahr | Jahr | Einstufung |
| --- | --- | --- | --- | ---: | ---: | --- |
| 2019 | PV | LZV | W | 10.386 | 3.767 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2019 | PV | VAP | W | 17.679 | 12.646 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2019 | PV-SELB | LZV | W | 871 | 142 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2019 | PV-SELB | SA2 | M | 2.691 | 3.421 | erklärt – plausibel: Schwerarbeitspension § 4 Abs. 3 APG: Entwicklung nach der Rechtslage (Übergangsrecht) – RD-04 |
| 2019 | PV-UNS | VAP | W | 13.529 | 8.543 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2019 | PV-UNS | LZV | W | 9.515 | 3.625 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2019 | PVA | VAP | W | 13.439 | 8.476 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2019 | PVA | LZV | W | 9.463 | 3.610 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2019 | PVA-ANG | LZV | W | 6.878 | 2.643 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2019 | PVA-ANG | VAP | W | 9.113 | 5.371 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2019 | PVA-ARB | VAP | W | 4.326 | 3.105 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2019 | PVA-ARB | LZV | W | 2.585 | 967 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2019 | SVA | SA1 | W | 232 | 298 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2019 | SVA | LZV | W | 374 | 132 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2019 | SVA | VAP | W | 606 | 430 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2019 | SVA | SA2 | M | 1.049 | 1.366 | erklärt – plausibel: Schwerarbeitspension § 4 Abs. 3 APG: Entwicklung nach der Rechtslage (Übergangsrecht) – RD-04 |
| 2019 | SVB | SA2 | M | 1.642 | 2.055 | erklärt – plausibel: Schwerarbeitspension § 4 Abs. 3 APG: Entwicklung nach der Rechtslage (Übergangsrecht) – RD-04 |
| 2019 | SVB | SA1 | M | 68 | 92 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2019 | SVB | LZV | W | 497 | 10 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2019 | VAEB | VAP | W | 90 | 67 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2019 | VAEB | LZV | W | 52 | 15 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2019 | VAEB-BB | LZV | M | 115 | 86 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2019 | VAEB-EB | SA2 | M | 144 | 195 | erklärt – plausibel: Schwerarbeitspension § 4 Abs. 3 APG: Entwicklung nach der Rechtslage (Übergangsrecht) – RD-04 |
| 2020 | PV | LZV | W | 3.767 | 1.504 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2020 | PV-SELB | LZV | W | 142 | 56 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2020 | PV-SELB | SA2 | M | 3.421 | 4.292 | erklärt – plausibel: Schwerarbeitspension § 4 Abs. 3 APG: Entwicklung nach der Rechtslage (Übergangsrecht) – RD-04 |
| 2020 | PV-UNS | LZV | W | 3.625 | 1.448 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2020 | PV-UNS | VAP | W | 8.543 | 6.010 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2020 | PVA | VAP | W | 8.476 | 5.952 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2020 | PVA | LZV | W | 3.610 | 1.442 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2020 | PVA-ANG | LZV | W | 2.643 | 1.044 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2020 | PVA-ANG | VAP | W | 5.371 | 3.535 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2020 | PVA-ARB | LZV | W | 967 | 398 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2021 | BVAEB | SA1 | W | 52 | 37 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2021 | BVAEB | VAP | W | 58 | 39 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2021 | PV | LZV | W | 1.504 | 483 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2021 | PV | VAP | W | 9.847 | 7.233 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2021 | PV-SELB | LZV | W | 56 | 18 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2021 | PV-UNS | VAP | W | 6.010 | 4.110 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2021 | PV-UNS | LZV | W | 1.448 | 465 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2021 | PVA | LZV | W | 1.442 | 463 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2021 | PVA | VAP | W | 5.952 | 4.071 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2021 | PVA-ANG | VAP | W | 3.535 | 2.304 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2021 | PVA-ANG | LZV | W | 1.044 | 335 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2021 | PVA-ARB | LZV | W | 398 | 128 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2021 | PVA-ARB | VAP | W | 2.417 | 1.767 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2021 | SVS | LZV | W | 56 | 18 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2021 | SVS-GW | LZV | W | 53 | 15 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2021 | SVS-LW | KOR | M | 81 | 111 | nicht erklärbar: an die Fachabteilung |
| 2021 | SVS-LW | LZV | M | 54 | 106 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2022 | BVAEB | SA1 | M | 90 | 55 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | BVAEB-BB | SA1 | M | 76 | 45 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | PV | SA1 | M | 3.035 | 1.875 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | PV | LZV | W | 483 | 0 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2022 | PV | SA1 | W | 6.749 | 4.487 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | PV | VAP | W | 7.233 | 4.487 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2022 | PV-SELB | SA1 | W | 3.105 | 2.122 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | PV-SELB | VAP | W | 3.123 | 2.122 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2022 | PV-SELB | SA1 | M | 226 | 159 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | PV-UNS | VAP | W | 4.110 | 2.365 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2022 | PV-UNS | SA1 | W | 3.644 | 2.365 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | PV-UNS | SA1 | M | 2.809 | 1.716 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | PV-UNS | LZV | W | 465 | 0 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2022 | PVA | SA1 | W | 3.607 | 2.346 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | PVA | SA1 | M | 2.719 | 1.661 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | PVA | LZV | W | 463 | 0 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2022 | PVA | VAP | W | 4.071 | 2.346 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2022 | PVA-ANG | LZV | W | 335 | 0 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2022 | PVA-ANG | SA1 | M | 773 | 465 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | PVA-ANG | SA1 | W | 1.969 | 1.287 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | PVA-ANG | VAP | W | 2.304 | 1.287 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2022 | PVA-ARB | VAP | W | 1.767 | 1.059 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2022 | PVA-ARB | LZV | W | 128 | 0 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2022 | PVA-ARB | SA1 | W | 1.638 | 1.059 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | PVA-ARB | SA1 | M | 1.946 | 1.196 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | SVS | VAP | W | 3.123 | 2.122 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2022 | SVS | SA1 | M | 226 | 159 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | SVS | SA1 | W | 3.105 | 2.122 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | SVS-GW | SA1 | W | 275 | 201 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | SVS-GW | SA1 | M | 138 | 83 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | SVS-GW | VAP | W | 290 | 201 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2022 | SVS-LW | LZV | M | 106 | 137 | nicht erklärbar: Langzeitversichertenregelung („Hacklerregelung“): Übergangsrecht/Altersgrenzen – Rückfrage an die Fachabteilung empfohlen |
| 2022 | SVS-LW | SA1 | W | 2.830 | 1.921 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2022 | SVS-LW | VAP | W | 2.833 | 1.921 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2023 | BVAEB | SA1 | M | 55 | 19 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | PV | VAP | W | 4.487 | 1.558 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2023 | PV | SA1 | M | 1.875 | 654 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | PV | SA1 | W | 4.487 | 1.557 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | PV-SELB | VAP | W | 2.122 | 747 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2023 | PV-SELB | SA1 | W | 2.122 | 747 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | PV-SELB | SA1 | M | 159 | 60 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | PV-UNS | VAP | W | 2.365 | 811 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2023 | PV-UNS | SA1 | M | 1.716 | 594 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | PV-UNS | SA1 | W | 2.365 | 810 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | PVA | VAP | W | 2.346 | 803 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2023 | PVA | SA1 | W | 2.346 | 802 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | PVA | SA1 | M | 1.661 | 575 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | PVA-ANG | SA1 | M | 465 | 155 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | PVA-ANG | SA1 | W | 1.287 | 450 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | PVA-ANG | VAP | W | 1.287 | 451 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2023 | PVA-ARB | SA1 | W | 1.059 | 352 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | PVA-ARB | SA1 | M | 1.196 | 420 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | PVA-ARB | VAP | W | 1.059 | 352 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2023 | SVS | VAP | W | 2.122 | 747 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2023 | SVS | SA1 | M | 159 | 60 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | SVS | SA1 | W | 2.122 | 747 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | SVS-GW | SA1 | M | 83 | 33 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | SVS-GW | VAP | W | 201 | 76 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2023 | SVS-GW | SA1 | W | 201 | 76 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | SVS-LW | SA1 | W | 1.921 | 671 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2023 | SVS-LW | VAP | W | 1.921 | 671 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2023 | SVS-LW | SA1 | M | 76 | 27 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | PV | SA1 | W | 1.557 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | PV | VAP | W | 1.558 | 129 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2024 | PV | SA1 | M | 654 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | PV-SELB | SA1 | M | 60 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | PV-SELB | SA1 | W | 747 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | PV-SELB | VAP | W | 747 | 54 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2024 | PV-UNS | VAP | W | 811 | 75 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2024 | PV-UNS | SA1 | W | 810 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | PV-UNS | SA1 | M | 594 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | PVA | SA1 | M | 575 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | PVA | VAP | W | 803 | 75 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2024 | PVA | SA1 | W | 802 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | PVA-ANG | VAP | W | 451 | 32 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2024 | PVA-ANG | SA1 | W | 450 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | PVA-ANG | SA1 | M | 155 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | PVA-ARB | SA1 | W | 352 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | PVA-ARB | SA1 | M | 420 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | PVA-ARB | VAP | W | 352 | 43 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2024 | SVS | SA1 | M | 60 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | SVS | SA1 | W | 747 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | SVS | VAP | W | 747 | 54 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2024 | SVS-GW | SA1 | W | 76 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2024 | SVS-GW | VAP | W | 76 | 6 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2024 | SVS-LW | VAP | W | 671 | 48 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2024 | SVS-LW | SA1 | W | 671 | 0 | erklärt – plausibel: Schwerarbeitspension § 607 Abs. 14 ASVG läuft aus (Übergangsrecht) – RD-04 |
| 2025 | PV | VAP | W | 129 | 567 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2025 | PV | SA2 | W | 128 | 566 | erklärt – plausibel: Schwerarbeitspension § 4 Abs. 3 APG: steigendes Frauenpensionsalter macht Frauen erstmals anspruchsberechtigt – RD-04 |
| 2025 | PV-SELB | VAP | W | 54 | 254 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2025 | PV-SELB | SA2 | W | 54 | 254 | erklärt – plausibel: Schwerarbeitspension § 4 Abs. 3 APG: steigendes Frauenpensionsalter macht Frauen erstmals anspruchsberechtigt – RD-04 |
| 2025 | PV-UNS | SA2 | W | 74 | 312 | erklärt – plausibel: Schwerarbeitspension § 4 Abs. 3 APG: steigendes Frauenpensionsalter macht Frauen erstmals anspruchsberechtigt – RD-04 |
| 2025 | PV-UNS | VAP | W | 75 | 313 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2025 | PVA | VAP | W | 75 | 309 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2025 | PVA | SA2 | W | 74 | 308 | erklärt – plausibel: Schwerarbeitspension § 4 Abs. 3 APG: steigendes Frauenpensionsalter macht Frauen erstmals anspruchsberechtigt – RD-04 |
| 2025 | SVS | VAP | W | 54 | 254 | erklärt – plausibel: Summe der vorzeitigen Alterspensionen – folgt den Arten oben |
| 2025 | SVS | SA2 | W | 54 | 254 | erklärt – plausibel: Schwerarbeitspension § 4 Abs. 3 APG: steigendes Frauenpensionsalter macht Frauen erstmals anspruchsberechtigt – RD-04 |
| 2025 | SVS-LW | GEM | W | 937 | 1.205 | nicht erklärbar: an die Fachabteilung |

Synthetische Daten für die KI Challenge – keine amtlichen Zahlen. Erzeugt von `python -m statagent pensionen`.
