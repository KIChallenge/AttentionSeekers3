# Kalibrierung gegen den Beispielbericht 08/2024

Erwartete Werte: `beispielbericht_2024-08.xlsx` wie geliefert (roh.cell, Tab1–Tab13); berechnete Werte: `stat_beschaeftigte` (Regelwerk basis, Stichtag 31.08.2024).

| Variante | Zellen | Abweichungen | Ergebnis |
| --- | ---: | ---: | --- |
| freigegebene Regeln (amtliche Werte) | 2880 | 359 | bestanden – Abweichungen vollständig durch R-DQ05 erklärt |
| Lesart des Beispielberichts für Geburtsmonat 13 (Alter = Jahr − Geburtsjahr, 370 Verhältnisse; nur zum Vergleich, nichts gespeichert) | 2880 | 0 | bestanden |

Insgesamt 392.236 Beschäftigungsverhältnisse.

Alle 359 Abweichungen liegen in der Altersgliederung (Tab13) und verschwinden, wenn die 370 Geburtsdaten mit Monat 13 wie im Beispielbericht gelesen werden. Die freigegebene Regel R-DQ05 liest sie bewusst mit vertauschtem Tag und Monat (Teamentscheidung, Problems.md DQ-05); Summen und Tab1–Tab12 stimmen exakt. Die Kalibrierung gilt damit als bestanden – mit erklärter, dokumentierter Abweichung.

Abweichungen mit den freigegebenen Regeln:

| Tabelle | Zelle | Beispielbericht | StatAgent | Differenz | Merkmal |
| --- | --- | ---: | ---: | ---: | --- |
| Tab13 | Z11S3 | 0 | 1 | +1 | Alter bis 14 Insgesamt M+F |
| Tab13 | Z11S4 | 0 | 1 | +1 | Alter bis 14 Insgesamt M |
| Tab13 | Z11S6 | 0 | 1 | +1 | Alter bis 14 Arbeiter M+F |
| Tab13 | Z11S7 | 0 | 1 | +1 | Alter bis 14 Arbeiter M |
| Tab13 | Z12S3 | 2917 | 2914 | -3 | Alter 15 Insgesamt M+F |
| Tab13 | Z12S4 | 1821 | 1819 | -2 | Alter 15 Insgesamt M |
| Tab13 | Z12S5 | 1096 | 1095 | -1 | Alter 15 Insgesamt W |
| Tab13 | Z12S6 | 2029 | 2027 | -2 | Alter 15 Arbeiter M+F |
| Tab13 | Z12S7 | 1463 | 1461 | -2 | Alter 15 Arbeiter M |
| Tab13 | Z12S9 | 888 | 887 | -1 | Alter 15 Angestellte und Beamte M+F |
| Tab13 | Z12S11 | 530 | 529 | -1 | Alter 15 Angestellte und Beamte W |
| Tab13 | Z13S3 | 3085 | 3083 | -2 | Alter 16 Insgesamt M+F |
| Tab13 | Z13S4 | 1869 | 1868 | -1 | Alter 16 Insgesamt M |
| Tab13 | Z13S5 | 1216 | 1215 | -1 | Alter 16 Insgesamt W |
| Tab13 | Z13S6 | 1990 | 1988 | -2 | Alter 16 Arbeiter M+F |
| Tab13 | Z13S7 | 1424 | 1423 | -1 | Alter 16 Arbeiter M |
| Tab13 | Z13S8 | 566 | 565 | -1 | Alter 16 Arbeiter W |
| Tab13 | Z14S3 | 3629 | 3624 | -5 | Alter 17 Insgesamt M+F |
| Tab13 | Z14S4 | 2195 | 2191 | -4 | Alter 17 Insgesamt M |
| Tab13 | Z14S5 | 1434 | 1433 | -1 | Alter 17 Insgesamt W |
| Tab13 | Z14S6 | 2273 | 2268 | -5 | Alter 17 Arbeiter M+F |
| Tab13 | Z14S7 | 1703 | 1699 | -4 | Alter 17 Arbeiter M |
| Tab13 | Z14S8 | 570 | 569 | -1 | Alter 17 Arbeiter W |
| Tab13 | Z15S3 | 4241 | 4237 | -4 | Alter 18 Insgesamt M+F |
| Tab13 | Z15S4 | 2392 | 2388 | -4 | Alter 18 Insgesamt M |
| Tab13 | Z15S6 | 2558 | 2556 | -2 | Alter 18 Arbeiter M+F |
| Tab13 | Z15S7 | 1822 | 1820 | -2 | Alter 18 Arbeiter M |
| Tab13 | Z15S9 | 1683 | 1681 | -2 | Alter 18 Angestellte und Beamte M+F |
| Tab13 | Z15S10 | 570 | 568 | -2 | Alter 18 Angestellte und Beamte M |
| Tab13 | Z17S3 | 5539 | 5536 | -3 | Alter 20 Insgesamt M+F |
| Tab13 | Z17S4 | 3112 | 3110 | -2 | Alter 20 Insgesamt M |
| Tab13 | Z17S5 | 2427 | 2426 | -1 | Alter 20 Insgesamt W |
| Tab13 | Z17S6 | 2530 | 2529 | -1 | Alter 20 Arbeiter M+F |
| Tab13 | Z17S7 | 1842 | 1841 | -1 | Alter 20 Arbeiter M |
| Tab13 | Z17S9 | 3009 | 3007 | -2 | Alter 20 Angestellte und Beamte M+F |
| Tab13 | Z17S10 | 1270 | 1269 | -1 | Alter 20 Angestellte und Beamte M |
| Tab13 | Z17S11 | 1739 | 1738 | -1 | Alter 20 Angestellte und Beamte W |
| Tab13 | Z18S3 | 5963 | 5959 | -4 | Alter 21 Insgesamt M+F |
| Tab13 | Z18S4 | 3292 | 3288 | -4 | Alter 21 Insgesamt M |
| Tab13 | Z18S6 | 2482 | 2478 | -4 | Alter 21 Arbeiter M+F |
| Tab13 | Z18S7 | 1839 | 1835 | -4 | Alter 21 Arbeiter M |
| Tab13 | Z19S3 | 6635 | 6630 | -5 | Alter 22 Insgesamt M+F |
| Tab13 | Z19S4 | 3653 | 3650 | -3 | Alter 22 Insgesamt M |
| Tab13 | Z19S5 | 2982 | 2980 | -2 | Alter 22 Insgesamt W |
| Tab13 | Z19S6 | 2663 | 2659 | -4 | Alter 22 Arbeiter M+F |
| Tab13 | Z19S7 | 2005 | 2002 | -3 | Alter 22 Arbeiter M |
| Tab13 | Z19S8 | 658 | 657 | -1 | Alter 22 Arbeiter W |
| Tab13 | Z19S9 | 3972 | 3971 | -1 | Alter 22 Angestellte und Beamte M+F |
| Tab13 | Z19S11 | 2324 | 2323 | -1 | Alter 22 Angestellte und Beamte W |
| Tab13 | Z20S3 | 6888 | 6885 | -3 | Alter 23 Insgesamt M+F |
| Tab13 | Z20S4 | 3764 | 3763 | -1 | Alter 23 Insgesamt M |
| Tab13 | Z20S5 | 3124 | 3122 | -2 | Alter 23 Insgesamt W |
| Tab13 | Z20S6 | 2552 | 2551 | -1 | Alter 23 Arbeiter M+F |
| Tab13 | Z20S7 | 1972 | 1971 | -1 | Alter 23 Arbeiter M |
| Tab13 | Z20S9 | 4336 | 4334 | -2 | Alter 23 Angestellte und Beamte M+F |
| Tab13 | Z20S11 | 2544 | 2542 | -2 | Alter 23 Angestellte und Beamte W |
| Tab13 | Z21S3 | 7563 | 7562 | -1 | Alter 24 Insgesamt M+F |
| Tab13 | Z21S5 | 3450 | 3449 | -1 | Alter 24 Insgesamt W |
| Tab13 | Z21S6 | 2734 | 2735 | +1 | Alter 24 Arbeiter M+F |
| Tab13 | Z21S7 | 2090 | 2091 | +1 | Alter 24 Arbeiter M |
| Tab13 | Z21S9 | 4829 | 4827 | -2 | Alter 24 Angestellte und Beamte M+F |
| Tab13 | Z21S10 | 2023 | 2022 | -1 | Alter 24 Angestellte und Beamte M |
| Tab13 | Z21S11 | 2806 | 2805 | -1 | Alter 24 Angestellte und Beamte W |
| Tab13 | Z22S3 | 7809 | 7806 | -3 | Alter 25 Insgesamt M+F |
| Tab13 | Z22S4 | 4342 | 4340 | -2 | Alter 25 Insgesamt M |
| Tab13 | Z22S5 | 3467 | 3466 | -1 | Alter 25 Insgesamt W |
| Tab13 | Z22S6 | 2739 | 2738 | -1 | Alter 25 Arbeiter M+F |
| Tab13 | Z22S7 | 2111 | 2110 | -1 | Alter 25 Arbeiter M |
| Tab13 | Z22S9 | 5070 | 5068 | -2 | Alter 25 Angestellte und Beamte M+F |
| Tab13 | Z22S10 | 2231 | 2230 | -1 | Alter 25 Angestellte und Beamte M |
| Tab13 | Z22S11 | 2839 | 2838 | -1 | Alter 25 Angestellte und Beamte W |
| Tab13 | Z23S3 | 8253 | 8248 | -5 | Alter 26 Insgesamt M+F |
| Tab13 | Z23S4 | 4645 | 4642 | -3 | Alter 26 Insgesamt M |
| Tab13 | Z23S5 | 3608 | 3606 | -2 | Alter 26 Insgesamt W |
| Tab13 | Z23S6 | 2797 | 2795 | -2 | Alter 26 Arbeiter M+F |
| Tab13 | Z23S7 | 2177 | 2175 | -2 | Alter 26 Arbeiter M |
| Tab13 | Z23S9 | 5456 | 5453 | -3 | Alter 26 Angestellte und Beamte M+F |
| Tab13 | Z23S10 | 2468 | 2467 | -1 | Alter 26 Angestellte und Beamte M |
| Tab13 | Z23S11 | 2988 | 2986 | -2 | Alter 26 Angestellte und Beamte W |
| Tab13 | Z24S3 | 8615 | 8614 | -1 | Alter 27 Insgesamt M+F |
| Tab13 | Z24S5 | 3789 | 3788 | -1 | Alter 27 Insgesamt W |
| Tab13 | Z24S6 | 2821 | 2822 | +1 | Alter 27 Arbeiter M+F |
| Tab13 | Z24S7 | 2233 | 2234 | +1 | Alter 27 Arbeiter M |
| Tab13 | Z24S9 | 5794 | 5792 | -2 | Alter 27 Angestellte und Beamte M+F |
| Tab13 | Z24S10 | 2593 | 2592 | -1 | Alter 27 Angestellte und Beamte M |
| Tab13 | Z24S11 | 3201 | 3200 | -1 | Alter 27 Angestellte und Beamte W |
| Tab13 | Z25S3 | 8794 | 8790 | -4 | Alter 28 Insgesamt M+F |
| Tab13 | Z25S4 | 5010 | 5007 | -3 | Alter 28 Insgesamt M |
| Tab13 | Z25S5 | 3784 | 3783 | -1 | Alter 28 Insgesamt W |
| Tab13 | Z25S6 | 2873 | 2872 | -1 | Alter 28 Arbeiter M+F |
| Tab13 | Z25S7 | 2264 | 2263 | -1 | Alter 28 Arbeiter M |
| Tab13 | Z25S9 | 5921 | 5918 | -3 | Alter 28 Angestellte und Beamte M+F |
| Tab13 | Z25S10 | 2746 | 2744 | -2 | Alter 28 Angestellte und Beamte M |
| Tab13 | Z25S11 | 3175 | 3174 | -1 | Alter 28 Angestellte und Beamte W |
| Tab13 | Z26S3 | 8776 | 8772 | -4 | Alter 29 Insgesamt M+F |
| Tab13 | Z26S4 | 5094 | 5092 | -2 | Alter 29 Insgesamt M |
| Tab13 | Z26S5 | 3682 | 3680 | -2 | Alter 29 Insgesamt W |
| Tab13 | Z26S9 | 5832 | 5828 | -4 | Alter 29 Angestellte und Beamte M+F |
| Tab13 | Z26S10 | 2766 | 2764 | -2 | Alter 29 Angestellte und Beamte M |
| Tab13 | Z26S11 | 3066 | 3064 | -2 | Alter 29 Angestellte und Beamte W |
| Tab13 | Z27S3 | 9017 | 9013 | -4 | Alter 30 Insgesamt M+F |
| Tab13 | Z27S4 | 5288 | 5285 | -3 | Alter 30 Insgesamt M |
| Tab13 | Z27S5 | 3729 | 3728 | -1 | Alter 30 Insgesamt W |
| Tab13 | Z27S6 | 3087 | 3083 | -4 | Alter 30 Arbeiter M+F |
| Tab13 | Z27S7 | 2448 | 2446 | -2 | Alter 30 Arbeiter M |
| Tab13 | Z27S8 | 639 | 637 | -2 | Alter 30 Arbeiter W |
| Tab13 | Z27S10 | 2840 | 2839 | -1 | Alter 30 Angestellte und Beamte M |
| Tab13 | Z27S11 | 3090 | 3091 | +1 | Alter 30 Angestellte und Beamte W |
| Tab13 | Z28S3 | 9265 | 9264 | -1 | Alter 31 Insgesamt M+F |
| Tab13 | Z28S4 | 5395 | 5394 | -1 | Alter 31 Insgesamt M |
| Tab13 | Z28S9 | 6121 | 6120 | -1 | Alter 31 Angestellte und Beamte M+F |
| Tab13 | Z28S10 | 2966 | 2965 | -1 | Alter 31 Angestellte und Beamte M |
| Tab13 | Z29S3 | 9473 | 9468 | -5 | Alter 32 Insgesamt M+F |
| Tab13 | Z29S4 | 5509 | 5505 | -4 | Alter 32 Insgesamt M |
| Tab13 | Z29S5 | 3964 | 3963 | -1 | Alter 32 Insgesamt W |
| Tab13 | Z29S6 | 3183 | 3181 | -2 | Alter 32 Arbeiter M+F |
| Tab13 | Z29S7 | 2534 | 2532 | -2 | Alter 32 Arbeiter M |
| Tab13 | Z29S9 | 6290 | 6287 | -3 | Alter 32 Angestellte und Beamte M+F |
| Tab13 | Z29S10 | 2975 | 2973 | -2 | Alter 32 Angestellte und Beamte M |
| Tab13 | Z29S11 | 3315 | 3314 | -1 | Alter 32 Angestellte und Beamte W |
| Tab13 | Z30S3 | 9283 | 9282 | -1 | Alter 33 Insgesamt M+F |
| Tab13 | Z30S4 | 5337 | 5335 | -2 | Alter 33 Insgesamt M |
| Tab13 | Z30S5 | 3946 | 3947 | +1 | Alter 33 Insgesamt W |
| Tab13 | Z30S9 | 6193 | 6192 | -1 | Alter 33 Angestellte und Beamte M+F |
| Tab13 | Z30S10 | 2935 | 2933 | -2 | Alter 33 Angestellte und Beamte M |
| Tab13 | Z30S11 | 3258 | 3259 | +1 | Alter 33 Angestellte und Beamte W |
| Tab13 | Z31S3 | 9479 | 9463 | -16 | Alter 34 Insgesamt M+F |
| Tab13 | Z31S4 | 5388 | 5381 | -7 | Alter 34 Insgesamt M |
| Tab13 | Z31S5 | 4091 | 4082 | -9 | Alter 34 Insgesamt W |
| Tab13 | Z31S6 | 3263 | 3258 | -5 | Alter 34 Arbeiter M+F |
| Tab13 | Z31S7 | 2495 | 2491 | -4 | Alter 34 Arbeiter M |
| Tab13 | Z31S8 | 768 | 767 | -1 | Alter 34 Arbeiter W |
| Tab13 | Z31S9 | 6216 | 6205 | -11 | Alter 34 Angestellte und Beamte M+F |
| Tab13 | Z31S10 | 2893 | 2890 | -3 | Alter 34 Angestellte und Beamte M |
| Tab13 | Z31S11 | 3323 | 3315 | -8 | Alter 34 Angestellte und Beamte W |
| Tab13 | Z32S3 | 9483 | 9481 | -2 | Alter 35 Insgesamt M+F |
| Tab13 | Z32S4 | 5319 | 5318 | -1 | Alter 35 Insgesamt M |
| Tab13 | Z32S5 | 4164 | 4163 | -1 | Alter 35 Insgesamt W |
| Tab13 | Z32S9 | 6288 | 6286 | -2 | Alter 35 Angestellte und Beamte M+F |
| Tab13 | Z32S10 | 2955 | 2954 | -1 | Alter 35 Angestellte und Beamte M |
| Tab13 | Z32S11 | 3333 | 3332 | -1 | Alter 35 Angestellte und Beamte W |
| Tab13 | Z33S3 | 9474 | 9470 | -4 | Alter 36 Insgesamt M+F |
| Tab13 | Z33S4 | 5261 | 5259 | -2 | Alter 36 Insgesamt M |
| Tab13 | Z33S5 | 4213 | 4211 | -2 | Alter 36 Insgesamt W |
| Tab13 | Z33S6 | 3143 | 3142 | -1 | Alter 36 Arbeiter M+F |
| Tab13 | Z33S8 | 794 | 793 | -1 | Alter 36 Arbeiter W |
| Tab13 | Z33S9 | 6331 | 6328 | -3 | Alter 36 Angestellte und Beamte M+F |
| Tab13 | Z33S10 | 2912 | 2910 | -2 | Alter 36 Angestellte und Beamte M |
| Tab13 | Z33S11 | 3419 | 3418 | -1 | Alter 36 Angestellte und Beamte W |
| Tab13 | Z34S3 | 9460 | 9451 | -9 | Alter 37 Insgesamt M+F |
| Tab13 | Z34S4 | 5174 | 5171 | -3 | Alter 37 Insgesamt M |
| Tab13 | Z34S5 | 4286 | 4280 | -6 | Alter 37 Insgesamt W |
| Tab13 | Z34S6 | 3111 | 3109 | -2 | Alter 37 Arbeiter M+F |
| Tab13 | Z34S8 | 839 | 837 | -2 | Alter 37 Arbeiter W |
| Tab13 | Z34S9 | 6349 | 6342 | -7 | Alter 37 Angestellte und Beamte M+F |
| Tab13 | Z34S10 | 2902 | 2899 | -3 | Alter 37 Angestellte und Beamte M |
| Tab13 | Z34S11 | 3447 | 3443 | -4 | Alter 37 Angestellte und Beamte W |
| Tab13 | Z35S3 | 9494 | 9487 | -7 | Alter 38 Insgesamt M+F |
| Tab13 | Z35S4 | 5147 | 5142 | -5 | Alter 38 Insgesamt M |
| Tab13 | Z35S5 | 4347 | 4345 | -2 | Alter 38 Insgesamt W |
| Tab13 | Z35S6 | 3175 | 3172 | -3 | Alter 38 Arbeiter M+F |
| Tab13 | Z35S7 | 2288 | 2285 | -3 | Alter 38 Arbeiter M |
| Tab13 | Z35S9 | 6319 | 6315 | -4 | Alter 38 Angestellte und Beamte M+F |
| Tab13 | Z35S10 | 2859 | 2857 | -2 | Alter 38 Angestellte und Beamte M |
| Tab13 | Z35S11 | 3460 | 3458 | -2 | Alter 38 Angestellte und Beamte W |
| Tab13 | Z36S3 | 9644 | 9643 | -1 | Alter 39 Insgesamt M+F |
| Tab13 | Z36S4 | 5164 | 5162 | -2 | Alter 39 Insgesamt M |
| Tab13 | Z36S5 | 4480 | 4481 | +1 | Alter 39 Insgesamt W |
| Tab13 | Z36S6 | 3259 | 3257 | -2 | Alter 39 Arbeiter M+F |
| Tab13 | Z36S7 | 2375 | 2373 | -2 | Alter 39 Arbeiter M |
| Tab13 | Z36S9 | 6385 | 6386 | +1 | Alter 39 Angestellte und Beamte M+F |
| Tab13 | Z36S11 | 3596 | 3597 | +1 | Alter 39 Angestellte und Beamte W |
| Tab13 | Z37S3 | 9602 | 9596 | -6 | Alter 40 Insgesamt M+F |
| Tab13 | Z37S4 | 5072 | 5070 | -2 | Alter 40 Insgesamt M |
| Tab13 | Z37S5 | 4530 | 4526 | -4 | Alter 40 Insgesamt W |
| Tab13 | Z37S6 | 3165 | 3166 | +1 | Alter 40 Arbeiter M+F |
| Tab13 | Z37S8 | 895 | 896 | +1 | Alter 40 Arbeiter W |
| Tab13 | Z37S9 | 6437 | 6430 | -7 | Alter 40 Angestellte und Beamte M+F |
| Tab13 | Z37S10 | 2802 | 2800 | -2 | Alter 40 Angestellte und Beamte M |
| Tab13 | Z37S11 | 3635 | 3630 | -5 | Alter 40 Angestellte und Beamte W |
| Tab13 | Z38S3 | 9832 | 9829 | -3 | Alter 41 Insgesamt M+F |
| Tab13 | Z38S4 | 5157 | 5156 | -1 | Alter 41 Insgesamt M |
| Tab13 | Z38S5 | 4675 | 4673 | -2 | Alter 41 Insgesamt W |
| Tab13 | Z38S9 | 6501 | 6498 | -3 | Alter 41 Angestellte und Beamte M+F |
| Tab13 | Z38S10 | 2765 | 2764 | -1 | Alter 41 Angestellte und Beamte M |
| Tab13 | Z38S11 | 3736 | 3734 | -2 | Alter 41 Angestellte und Beamte W |
| Tab13 | Z39S3 | 9952 | 9945 | -7 | Alter 42 Insgesamt M+F |
| Tab13 | Z39S4 | 5156 | 5152 | -4 | Alter 42 Insgesamt M |
| Tab13 | Z39S5 | 4796 | 4793 | -3 | Alter 42 Insgesamt W |
| Tab13 | Z39S6 | 3406 | 3401 | -5 | Alter 42 Arbeiter M+F |
| Tab13 | Z39S7 | 2388 | 2386 | -2 | Alter 42 Arbeiter M |
| Tab13 | Z39S8 | 1018 | 1015 | -3 | Alter 42 Arbeiter W |
| Tab13 | Z39S9 | 6546 | 6544 | -2 | Alter 42 Angestellte und Beamte M+F |
| Tab13 | Z39S10 | 2768 | 2766 | -2 | Alter 42 Angestellte und Beamte M |
| Tab13 | Z40S3 | 10079 | 10072 | -7 | Alter 43 Insgesamt M+F |
| Tab13 | Z40S4 | 5270 | 5265 | -5 | Alter 43 Insgesamt M |
| Tab13 | Z40S5 | 4809 | 4807 | -2 | Alter 43 Insgesamt W |
| Tab13 | Z40S6 | 3421 | 3419 | -2 | Alter 43 Arbeiter M+F |
| Tab13 | Z40S7 | 2381 | 2379 | -2 | Alter 43 Arbeiter M |
| Tab13 | Z40S9 | 6658 | 6653 | -5 | Alter 43 Angestellte und Beamte M+F |
