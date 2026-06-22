#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spatio-temporaler Spatial Neighbor Consistency Test (SNCT).

Der SNCT wird als k-nearest-neighbor-Konsistenzmaß berechnet:
Für jeden Beleg werden die k nächsten Nachbarn im standardisierten Raum-Zeit-Raum
(X, Y, Jahr) bestimmt. Der Score gibt an, welcher Anteil dieser Nachbarn dieselbe
Variantenklassifikation aufweist.

Aufruf:
python scripts/02_spatiotemporal_snct.py --input data/Diphthongierung.csv --outdir output/tables
"""

from __future__ import annotations

import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

VARIABLES = {
    "Wein": {"mono": "i", "diph": "ei"},
    "Haus": {"mono": "u", "diph": "au"},
}


def parse_number(value):
    if pd.isna(value):
        return np.nan
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return np.nan


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, sep=";", engine="python")
    except UnicodeDecodeError:
        return pd.read_csv(path, sep=";", engine="python", encoding="latin1")


def prepare(df: pd.DataFrame, variable: str) -> pd.DataFrame:
    spec = VARIABLES[variable]
    data = df.copy()
    data["X_num"] = data["X"].apply(parse_number)
    data["Y_num"] = data["Y"].apply(parse_number)
    # Dieses Skript folgt dem im Artikel berichteten SNCT: nur exakt numerisch fassbare Jahresangaben.
    data["Jahr_num"] = pd.to_numeric(data["Jahr eigene"], errors="coerce")
    data["variant_bin"] = data[variable].map({spec["mono"]: 0, spec["diph"]: 1})
    return data.dropna(subset=["X_num", "Y_num", "Jahr_num", "variant_bin"]).copy()


def snct(data: pd.DataFrame, k: int = 5) -> dict:
    coords = data[["X_num", "Y_num", "Jahr_num"]].to_numpy(float)
    coords_scaled = StandardScaler().fit_transform(coords)
    labels = data["variant_bin"].to_numpy(int)
    nn = NearestNeighbors(n_neighbors=k + 1, algorithm="ball_tree").fit(coords_scaled)
    _, indices = nn.kneighbors(coords_scaled)
    scores = []
    for i in range(len(data)):
        neighbor_labels = labels[indices[i][1:]]
        scores.append(np.mean(neighbor_labels == labels[i]))
    return {
        "N": len(data),
        "k": k,
        "SNCT": float(np.mean(scores)),
        "SNCT_percent": float(np.mean(scores) * 100),
        "N_mono": int(np.sum(labels == 0)),
        "N_diph": int(np.sum(labels == 1)),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/Diphthongierung.csv")
    parser.add_argument("--outdir", default="output/tables")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    df = read_csv(Path(args.input))
    rows = []
    for variable in VARIABLES:
        data = prepare(df, variable)
        res = snct(data, k=args.k)
        res["Leitform"] = variable
        rows.append(res)
        data.to_csv(outdir / f"snct_daten_{variable.lower()}.csv", index=False)
    out = pd.DataFrame(rows)[["Leitform", "N", "k", "SNCT", "SNCT_percent", "N_mono", "N_diph"]]
    out.to_csv(outdir / "spatiotemporal_snct_results.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
