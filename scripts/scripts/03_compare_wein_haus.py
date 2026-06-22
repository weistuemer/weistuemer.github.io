#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Makrovergleich der Diphthongierung bei Wein und Haus.

Erzeugt:
- Vergleich_Timeline.png
- Statistik_Vergleich_Scatter.png
- vergleich_wein_haus_timeline.csv
- vergleich_wein_haus_regionen.csv

Aufruf:
python scripts/03_compare_wein_haus.py --input data/Diphthongierung.csv --outdir output
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

C_WEIN = "#5ab4ac"
C_HAUS = "#d8b365"
REGION_ORDER = ["CH", "Elsass", "WOD", "MDT", "WMD", "NDT", "OOD"]


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, sep=";", engine="python")
    except UnicodeDecodeError:
        return pd.read_csv(path, sep=";", engine="python", encoding="latin1")


def extract_year(value):
    m = re.search(r"\b(1[2-9]\d{2})\b", str(value))
    return int(m.group(1)) if m else np.nan


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/Diphthongierung.csv")
    parser.add_argument("--outdir", default="output")
    args = parser.parse_args()
    outdir = Path(args.outdir)
    (outdir / "figures").mkdir(parents=True, exist_ok=True)
    (outdir / "tables").mkdir(parents=True, exist_ok=True)

    df = read_csv(Path(args.input))
    df["Year"] = df["Jahr eigene"].apply(extract_year)
    df = df[(df["Year"] >= 1200) & (df["Year"] <= 1700)].copy()
    df["Wein_Clean"] = df["Wein"].astype(str).str.strip().replace({"I": "i"})
    df["Haus_Clean"] = df["Haus"].astype(str).str.strip()

    df["Period30"] = (df["Year"] // 30) * 30
    timeline = df.groupby("Period30").apply(
    lambda x: pd.Series({
        "Wein_N": x["Wein_Clean"].isin(["i", "ei"]).sum(),
        "Wein_Ei": (x["Wein_Clean"] == "ei").sum(),
        "Haus_N": x["Haus_Clean"].isin(["u", "au"]).sum(),
        "Haus_Au": (x["Haus_Clean"] == "au").sum(),
    }),
    include_groups=False
).reset_index()
    timeline = timeline[(timeline["Wein_N"] > 2) | (timeline["Haus_N"] > 2)].copy()
    timeline["Rate_Wein"] = timeline["Wein_Ei"] / timeline["Wein_N"]
    timeline["Rate_Haus"] = timeline["Haus_Au"] / timeline["Haus_N"]
    timeline.to_csv(outdir / "tables" / "vergleich_wein_haus_timeline.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(timeline["Period30"], timeline["Rate_Wein"], label="Wein (î > ei)", color=C_WEIN, marker="o", lw=2.5, alpha=0.9)
    ax.plot(timeline["Period30"], timeline["Rate_Haus"], label="Haus (û > au)", color=C_HAUS, marker="s", lw=2.5, alpha=0.9, linestyle="--")
    ax.set_xlabel("Jahr (30-Jahres-Schritte)")
    ax.set_ylabel("Anteil Diphthongierung")
    ax.set_ylim(-0.05, 1.05)
    ax.legend()
    ax.grid(True, alpha=0.3, linestyle="--")
    fig.tight_layout()
    fig.savefig(outdir / "figures" / "Vergleich_Timeline.png", dpi=300)
    plt.close(fig)

    df_late = df[df["Year"] >= 1400]
    stats = []
    for reg in REGION_ORDER:
        d = df_late[df_late["Region eigene"] == reg]
        if len(d) < 5:
            continue
        w_n = d["Wein_Clean"].isin(["i", "ei"]).sum()
        h_n = d["Haus_Clean"].isin(["u", "au"]).sum()
        stats.append({
            "Region": reg,
            "Wein_N": int(w_n),
            "Wein_rate": (d["Wein_Clean"] == "ei").sum() / w_n if w_n else np.nan,
            "Haus_N": int(h_n),
            "Haus_rate": (d["Haus_Clean"] == "au").sum() / h_n if h_n else np.nan,
        })
    df_reg = pd.DataFrame(stats)
    df_reg.to_csv(outdir / "tables" / "vergleich_wein_haus_regionen.csv", index=False)

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(df_reg))
    width = 0.35
    ax.bar(x - width / 2, df_reg["Wein_rate"], width, label="Wein (ei)", color=C_WEIN, alpha=0.9)
    ax.bar(x + width / 2, df_reg["Haus_rate"], width, label="Haus (au)", color=C_HAUS, alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(df_reg["Region"])
    ax.set_ylabel("Diphthongierungsrate")
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(outdir / "figures" / "Statistik_Vergleich_Scatter.png", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
