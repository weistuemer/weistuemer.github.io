#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deskriptive Auswertung der Diphthongierung in den Grimmschen Weistümern.

Ausgaben:
- bereinigte Datentabelle
- Raten nach Region × 50-Jahres-Intervall
- Linienplots und Heatmaps für Wein und Haus
- Log-Likelihood/G-Tests für Region und Zeitraum
- explorativer zellenbasierter Vergleich mit Lindgren

Aufruf:
python scripts/01_descriptive_gtests_lindgren.py --input data/Diphthongierung.csv --outdir output
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import chi2_contingency, spearmanr

INTERVAL_WIDTH = 50
MIN_N_FOR_RATE = 5
MIN_N_FOR_SCATTER = 5
REGION_ORDER = ["NDT", "WMD", "MDT", "WOD", "Elsass", "CH", "OOD"]

VARIABLES = {
    "Wein": {"mono": "i", "diph": "ei", "mixed": "i_ei", "lindgren_col": "i_ai", "label": "mhd. î > ei"},
    "Haus": {"mono": "u", "diph": "au", "mixed": "u_au", "lindgren_col": "u_au", "label": "mhd. û > au"},
}

REGION_MAP_LINDGREN = {
    "OOD": "Bairisch",
    "MDT": "Ostfränkisch",
    "WOD": "Schwäbisch/Augsburg",
    "WMD": "Südfränkisch",
}

LINDGREN_ROWS = [
    ("Bairisch", 1250, 75.0, 100.0, "Wernhers Maria"),
    ("Bairisch", 1250, 50.0, 98.0, "Benedictinerregel"),
    ("Bairisch", 1300, 40.0, 85.0, "Melker Handschrift"),
    ("Bairisch", 1300, 5.0, 65.0, "Gundacker von Judenburg"),
    ("Bairisch", 1400, 99.9, 100.0, "Apollonius"),
    ("Bairisch", 1400, 98.0, 100.0, "Märterbuch"),
    ("Bairisch", 1400, 99.5, 100.0, "Deutsche Sphaera"),
    ("Bairisch", 1400, 99.9, 100.0, "Der große Alexander"),
    ("Bairisch", 1450, 100.0, 100.0, "Dietrichs erste Ausfahrt"),
    ("Bairisch", 1450, 99.9, 100.0, "Chronik der 95 Herrschaften"),
    ("Bairisch", 1500, 100.0, 100.0, "Merlin und Seifrid"),
    ("Bairisch", 1500, 100.0, 99.7, "Füetrers Lanzelot"),
    ("Bairisch", 1500, 99.95, 100.0, "Hans Folz"),
    ("Bairisch", 1500, 99.8, 100.0, "Fastnachtspiele"),
    ("Ostfränkisch", 1300, 4.0, 33.0, "Urkunden"),
    ("Ostfränkisch", 1350, 0.3, 0.6, "Johann von Würzburg"),
    ("Ostfränkisch", 1400, 2.0, 5.0, "Minneburg"),
    ("Ostfränkisch", 1500, 94.0, 80.0, "Erhard Wahraus"),
    ("Schwäbisch/Augsburg", 1300, 2.0, 25.0, "Schwäbische Urkunden"),
    ("Schwäbisch/Augsburg", 1300, 0.08, 0.0, "Ulrich von Türheim"),
    ("Schwäbisch/Augsburg", 1350, 0.0, 0.7, "Summa Theologica"),
    ("Schwäbisch/Augsburg", 1350, 0.2, 0.6, "Der elende Knabe"),
    ("Schwäbisch/Augsburg", 1350, 0.0, 0.0, "Margaretha Ebner"),
    ("Schwäbisch/Augsburg", 1400, 0.0, 0.0, "Oswaltprosa"),
    ("Schwäbisch/Augsburg", 1400, 15.0, 1.0, "Augsburger 1. Chronik"),
    ("Schwäbisch/Augsburg", 1400, 15.0, 35.0, "Schachgedicht"),
    ("Schwäbisch/Augsburg", 1450, 96.0, 60.0, "Augsburger Fortsetzung"),
    ("Schwäbisch/Augsburg", 1450, 91.0, 75.0, "Herzog Ernst Prosa"),
    ("Schwäbisch/Augsburg", 1450, 97.0, 98.0, "Heinrich Mynsinger"),
    ("Schwäbisch/Augsburg", 1450, 99.5, 92.0, "Heinrich Kaufringer"),
    ("Schwäbisch/Augsburg", 1450, 0.3, 0.2, "Herman von Sachsenheim"),
    ("Schwäbisch/Augsburg", 1500, 94.0, 80.0, "Erhard Wahraus"),
    ("Schwäbisch/Augsburg", 1500, 50.0, 96.0, "Nonne von Engelthal"),
    ("Südfränkisch", 1450, 0.1, 1.0, "Reinolt von Montelban"),
    ("Südfränkisch", 1450, 0.0, 0.0, "Prosa-Lancelot"),
    ("Südfränkisch", 1450, 0.0, 0.0, "Minnereden II"),
]


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, sep=";", engine="python")
    except UnicodeDecodeError:
        return pd.read_csv(path, sep=";", engine="python", encoding="latin1")


def parse_number(value):
    if pd.isna(value):
        return np.nan
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return np.nan


def parse_year(value):
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    if s.upper() in {"", "NN", "N.N.", "NAN"}:
        return np.nan
    m = re.search(r"(Anfang|Mitte|Ende)?\s*(\d{1,2})\s*\.\s*Jh", s, flags=re.IGNORECASE)
    if m:
        part = (m.group(1) or "Mitte").lower()
        century = int(m.group(2))
        base = (century - 1) * 100
        return base + {"anfang": 25, "mitte": 50, "ende": 75}.get(part, 50)
    m = re.search(r"(1[0-9]{3})", s)
    return float(m.group(1)) if m else np.nan


def make_interval(year, width=INTERVAL_WIDTH):
    if pd.isna(year):
        return np.nan
    start = int(np.floor(float(year) / width) * width)
    return f"{start}-{start + width - 1}"


def interval_sort_key(label):
    return int(str(label).split("-")[0])


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["X_num"] = df["X"].apply(parse_number)
    df["Y_num"] = df["Y"].apply(parse_number)
    df["year_num"] = df["Jahr eigene"].apply(parse_year)
    df["year_num"] = df["year_num"].fillna(df["Jahr"].apply(parse_year))
    df["interval"] = df["year_num"].apply(make_interval)
    for var, spec in VARIABLES.items():
        df[f"{var}_score"] = df[var].map({spec["mono"]: 0.0, spec["diph"]: 1.0, spec["mixed"]: 0.5})
        df[f"{var}_binary"] = df[var].map({spec["mono"]: 0.0, spec["diph"]: 1.0})
    return df


def compute_rates(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for var in VARIABLES:
        score_col = f"{var}_score"
        sub = df.dropna(subset=["Region eigene", "interval", score_col]).copy()
        g = sub.groupby(["Region eigene", "interval"], as_index=False)[score_col].agg(n="count", diph_score="sum")
        g["rate"] = g["diph_score"] / g["n"] * 100
        g.loc[g["n"] < MIN_N_FOR_RATE, "rate"] = np.nan
        g["Variable"] = var
        rows.append(g)
    return pd.concat(rows, ignore_index=True)


def save_line_plot(rates: pd.DataFrame, variable: str, outdir: Path):
    sub = rates[rates["Variable"] == variable]
    intervals = sorted(sub["interval"].dropna().unique(), key=interval_sort_key)
    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(intervals))
    for region in [r for r in REGION_ORDER if r in sub["Region eigene"].unique()]:
        y = []
        for interval in intervals:
            cell = sub[(sub["Region eigene"] == region) & (sub["interval"] == interval)]
            y.append(np.nan if cell.empty else cell["rate"].iloc[0])
        if np.isfinite(y).any():
            ax.plot(x, y, marker="o", linewidth=1.8, label=region)
    ax.set_ylabel("diphthongierte Varianten (%)")
    ax.set_xlabel("50-Jahres-Intervall")
    ax.set_ylim(-3, 103)
    ax.set_xticks(x)
    ax.set_xticklabels(intervals, rotation=45, ha="right")
    ax.grid(True, axis="y", linestyle="--", alpha=0.35)
    ax.legend(title="Region", bbox_to_anchor=(1.02, 1), loc="upper left")
    fig.tight_layout()
    fig.savefig(outdir / "figures" / f"linien_{variable.lower()}_regionen.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_heatmap(rates: pd.DataFrame, variable: str, outdir: Path):
    sub = rates[rates["Variable"] == variable]
    intervals = sorted(sub["interval"].dropna().unique(), key=interval_sort_key)
    mat = sub.pivot(index="Region eigene", columns="interval", values="rate")
    regions = [r for r in REGION_ORDER if r in mat.index]
    mat = mat.reindex(index=regions, columns=intervals)
    fig, ax = plt.subplots(figsize=(11, 4.8))
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="#eeeeee")
    im = ax.imshow(np.ma.masked_invalid(mat.to_numpy(float)), aspect="auto", vmin=0, vmax=100, cmap=cmap)
    ax.set_xlabel("50-Jahres-Intervall")
    ax.set_ylabel("Regionen, grob Nord → Süd")
    ax.set_xticks(np.arange(len(intervals)))
    ax.set_xticklabels(intervals, rotation=45, ha="right")
    ax.set_yticks(np.arange(len(regions)))
    ax.set_yticklabels(regions)
    ax.set_xticks(np.arange(-.5, len(intervals), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(regions), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1)
    ax.tick_params(which="minor", bottom=False, left=False)
    fig.colorbar(im, ax=ax, label="diphthongierte Varianten (%)")
    fig.tight_layout()
    fig.savefig(outdir / "figures" / f"heatmap_{variable.lower()}_regionen.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def g_tests(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for var in VARIABLES:
        for pred in ["Region eigene", "interval"]:
            sub = df.dropna(subset=[pred, f"{var}_binary"])
            table = pd.crosstab(sub[pred], sub[f"{var}_binary"])
            if table.shape[0] < 2 or table.shape[1] < 2:
                continue
            g2, p, dof, _ = chi2_contingency(table, lambda_="log-likelihood")
            n = table.to_numpy().sum()
            v = np.sqrt(g2 / (n * min(table.shape[0] - 1, table.shape[1] - 1)))
            rows.append({"Leitform": var, "Praediktor": pred, "G2": g2, "p": p, "df": dof, "Cramers_V": v, "n": int(n)})
    return pd.DataFrame(rows)


def lindgren_agg(outdir: Path) -> pd.DataFrame:
    lind = pd.DataFrame(LINDGREN_ROWS, columns=["Lindgren_Gruppe", "Jahr", "i_ai", "u_au", "Text"])
    lind["interval"] = lind["Jahr"].apply(make_interval)
    lind.to_csv(outdir / "tables" / "lindgren_referenz_eingabe.csv", index=False)
    agg = lind.groupby(["Lindgren_Gruppe", "interval"], as_index=False).agg(n=("Text", "count"), i_ai=("i_ai", "mean"), u_au=("u_au", "mean"))
    agg.to_csv(outdir / "tables" / "lindgren_referenz_aggregiert.csv", index=False)
    return agg


def lindgren_scatter(rates: pd.DataFrame, lind: pd.DataFrame, variable: str, outdir: Path) -> pd.DataFrame:
    col = VARIABLES[variable]["lindgren_col"]
    weis = rates[(rates["Variable"] == variable) & (rates["n"] >= MIN_N_FOR_SCATTER) & rates["Region eigene"].isin(REGION_MAP_LINDGREN)].copy()
    weis["Lindgren_Gruppe"] = weis["Region eigene"].map(REGION_MAP_LINDGREN)
    merged = weis.merge(lind[["Lindgren_Gruppe", "interval", col, "n"]].rename(columns={col: "lindgren_rate", "n": "n_lindgren"}), on=["Lindgren_Gruppe", "interval"], how="inner")
    merged = merged.rename(columns={"rate": "weisthuemer_rate", "n": "n_weisthuemer"})
    merged["Variable"] = variable
    merged["abs_diff"] = (merged["weisthuemer_rate"] - merged["lindgren_rate"]).abs()

    fig, ax = plt.subplots(figsize=(6.2, 6.2))
    if not merged.empty:
        sizes = 35 + merged["n_weisthuemer"].astype(float) * 7
        ax.scatter(merged["lindgren_rate"], merged["weisthuemer_rate"], s=sizes, alpha=0.7, edgecolor="black", linewidth=0.5)
        for _, r in merged.iterrows():
            ax.annotate(f"{r['Region eigene']}\n{r['interval']}", (r["lindgren_rate"], r["weisthuemer_rate"]), xytext=(4, 4), textcoords="offset points", fontsize=7)
    ax.plot([0, 100], [0, 100], linestyle="--", color="gray")
    ax.set_xlim(-3, 103); ax.set_ylim(-3, 103)
    ax.set_xlabel("Lindgren: diphthongierte Belege (%)")
    ax.set_ylabel("Weistümer: diphthongierte Leitformen (%)")
    ax.grid(True, linestyle="--", alpha=0.35)
    fig.tight_layout()
    fig.savefig(outdir / "figures" / f"vergleich_lindgren_weisthuemer_{variable.lower()}_scatter_min5.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    return merged


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/Diphthongierung.csv")
    parser.add_argument("--outdir", default="output")
    args = parser.parse_args()
    outdir = Path(args.outdir)
    (outdir / "figures").mkdir(parents=True, exist_ok=True)
    (outdir / "tables").mkdir(parents=True, exist_ok=True)

    df = prepare(read_csv(Path(args.input)))
    df.to_csv(outdir / "tables" / "diphthongierung_bereinigt.csv", index=False)
    rates = compute_rates(df)
    rates.to_csv(outdir / "tables" / "weisthuemer_raten_region_intervall.csv", index=False)
    for var in VARIABLES:
        save_line_plot(rates, var, outdir)
        save_heatmap(rates, var, outdir)
    g_tests(df).to_csv(outdir / "tables" / "loglikelihood_tests_weisthuemer.csv", index=False)

    lind = lindgren_agg(outdir)
    cells = pd.concat([lindgren_scatter(rates, lind, var, outdir) for var in VARIABLES], ignore_index=True)
    cells.to_csv(outdir / "tables" / "vergleich_lindgren_weisthuemer_scatter_zellen_min5.csv", index=False)
    stats = []
    for var in VARIABLES:
        sub = cells[cells["Variable"] == var]
        rho, p = spearmanr(sub["lindgren_rate"], sub["weisthuemer_rate"]) if len(sub) >= 3 else (np.nan, np.nan)
        stats.append({"Leitform": var, "Zellen": len(sub), "mittlere_absolute_Abweichung": sub["abs_diff"].mean(), "Spearman_rho": rho, "p": p})
    pd.DataFrame(stats).to_csv(outdir / "tables" / "vergleich_lindgren_weisthuemer_scatter_statistik_min5.csv", index=False)


if __name__ == "__main__":
    main()
