# -*- coding: utf-8 -*-
"""Construit le site web statique (docs/) : copie les figures + exporte data.js."""
import os, json, shutil
import pandas as pd, numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(BASE, "docs"); ASSETS = os.path.join(DOCS, "assets")
FIG = os.path.join(BASE, "reports", "figures"); PROC = os.path.join(BASE, "data", "processed")
MODELS = os.path.join(BASE, "models")
os.makedirs(ASSETS, exist_ok=True)

for f in os.listdir(FIG):
    if f.endswith(".png"):
        shutil.copy2(os.path.join(FIG, f), os.path.join(ASSETS, f))

fn = pd.read_csv(os.path.join(PROC, "fact_prix_national.csv"), parse_dates=["date"])
pan = pd.read_csv(os.path.join(PROC, "indice_panier_national.csv"), parse_dates=["date"])
comp = pd.read_csv(os.path.join(PROC, "inflation_compare.csv")).dropna()
fc = pd.read_csv(os.path.join(MODELS, "forecast_riz.csv"), parse_dates=["date"])
mc = pd.read_csv(os.path.join(MODELS, "model_comparison.csv"))

def serie(comm):
    g = fn[fn["commodity_fr"] == comm].sort_values("date")
    return [None if pd.isna(v) else round(float(v)) for v in g["prix_median"]]

labels = sorted(fn["date"].dt.strftime("%Y-%m").unique())
# aligner les séries sur labels
def aligned(comm):
    g = fn[fn["commodity_fr"] == comm].set_index(fn[fn["commodity_fr"]==comm]["date"].dt.strftime("%Y-%m"))["prix_median"]
    return [None if l not in g.index else round(float(g[l])) for l in labels]

g = fn.sort_values("date")
deb = g.groupby("commodity_fr").first()["prix_median"]; fin = g.groupby("commodity_fr").last()["prix_median"]
hausse = ((fin/deb-1)*100).dropna().sort_values(ascending=False)

riz_now = round(float(fn[fn.commodity_fr=="Riz importé (brisé)"].sort_values("date")["prix_median"].iloc[-1]))
data = {
    "labels": labels,
    "riz": aligned("Riz importé (brisé)"),
    "mil": aligned("Mil"),
    "mais": aligned("Maïs local"),
    "panier_labels": pan["date"].dt.strftime("%Y-%m").tolist(),
    "panier": [round(float(x),1) for x in pan["indice_panier"]],
    "panier_yoy": [None if pd.isna(v) else round(float(v),1) for v in pan["var_annuelle_pct"]],
    "comp_years": [int(x) for x in comp["annee"]],
    "comp_wfp": [round(float(x),1) for x in comp["inflation_alimentaire_WFP_%"]],
    "comp_off": [round(float(x),1) for x in comp["inflation_officielle_BM_%"]],
    "hausse_labels": hausse.head(8).index.tolist(),
    "hausse_values": [round(float(x)) for x in hausse.head(8).values],
    "forecast_labels": fc["date"].dt.strftime("%Y-%m").tolist(),
    "forecast": [round(float(x)) for x in fc["prix_prevu"]],
    "kpi": {
        "corr": round(float(comp["inflation_alimentaire_WFP_%"].corr(comp["inflation_officielle_BM_%"])),2),
        "crise2008": round(float(comp.set_index('annee').loc[2008,'inflation_alimentaire_WFP_%'])),
        "top_produit": hausse.index[0], "top_val": round(float(hausse.iloc[0])),
        "indice_now": round(float(pan["indice_panier"].iloc[-1])),
        "best_model": mc.iloc[0]["modele"], "mape": round(float(mc.iloc[0]["MAPE_%"]),1),
        "marches": 64, "riz_now": riz_now,
    },
}
with open(os.path.join(DOCS, "data.js"), "w", encoding="utf-8") as f:
    f.write("window.PROJECT_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n")
print("Site OK :", len(os.listdir(ASSETS)), "figures |", data["kpi"])
