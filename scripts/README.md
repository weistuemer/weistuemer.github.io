# Reproduktionsskripte: Diphthongierung in den Grimmschen Weistümern



## Daten

Die Basisdaten liegen in Datei `Diphthongierung.csv` im Ordner `data/`.



## Python-Packete

```bash
pip install pandas numpy matplotlib scipy scikit-learn
```



## R-Packete

```r
install.packages(c("tidyverse", "mgcv", "viridisLite"))
```



## Scripts

1. `scripts/01_descriptive_gtests_lindgren.py`  
   Bereinigung, Variantenkodierung, Aggregation nach Region und 50-Jahres-Intervallen, Linienplots, Heatmaps, Log-Likelihood/G-Tests, explorativer Lindgren-Abgleich.

2. `scripts/02_spatiotemporal_snct.py`  
   Spatio-temporaler Spatial Neighbor Consistency Test (SNCT) für `Wein` und `Haus`, k=5.

3. `scripts/03_compare_wein_haus.py`  
   Makrovergleich von `Wein` und `Haus`: Zeitverlauf und regionale Kopplung.

4. `scripts/04_separate_gams_wein_haus.R`  
   Getrennte binomiale GAMs für `Wein` und `Haus`; Mischformen werden ausgeschlossen.

5. `scripts/05_combined_gam_wein_haus.R`  
   Kombiniertes binomiales GAM mit lexemspezifischen raumzeitlichen Smooths; Mischformen werden ausgeschlossen.

6. `scripts/06_gam_effectplots_mgcv.R`  
   Effektplots aus den R/mgcv-Modellen für ausgewählte Zeitschnitte.

## Hinweis zur Kodierung

Für inferenzstatistische binomiale Modelle werden nur eindeutige Varianten genutzt:

- `Wein`: `i = 0`, `ei = 1`, Mischformen wie `i_ei` ausgeschlossen
- `Haus`: `u = 0`, `au = 1`, Mischformen wie `u_au` ausgeschlossen

Für deskriptive Aggregationen werden Mischformen anteilig als `0.5` gewertet.
