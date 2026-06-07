# -*- coding: utf-8 -*-
"""Construit les notebooks du projet (données réelles WFP + Banque mondiale)."""
import os
import nbformat as nbf

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NB_DIR = os.path.join(BASE, "notebooks")
os.makedirs(NB_DIR, exist_ok=True)

def build(path, cells):
    nb = nbf.v4.new_notebook()
    nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                      "language_info": {"name": "python"}}
    nb["cells"] = [nbf.v4.new_markdown_cell(s) if k == "md" else nbf.v4.new_code_cell(s) for k, s in cells]
    with open(path, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print("écrit :", os.path.relpath(path, BASE))

SETUP = r"""
import os, warnings, json
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams.update({"figure.figsize": (11, 5), "figure.dpi": 110, "axes.titlesize": 13})

PROJ = os.getcwd()
if not os.path.isdir(os.path.join(PROJ, "data")):
    PROJ = os.path.dirname(PROJ)
RAW = os.path.join(PROJ, "data", "raw")
PROC = os.path.join(PROJ, "data", "processed")
GEO = os.path.join(PROJ, "data", "geo")
FIG = os.path.join(PROJ, "reports", "figures")
MODELS = os.path.join(PROJ, "models")
for d in (PROC, FIG, MODELS):
    os.makedirs(d, exist_ok=True)

# Libellés FR des denrées et des régions
COMMOD_FR = {
    "Rice (imported)": "Riz importé (brisé)", "Rice (local)": "Riz local",
    "Rice (ordinary, first quality)": "Riz ordinaire 1re qual.",
    "Rice (ordinary, second quality)": "Riz ordinaire 2e qual.",
    "Millet": "Mil", "Sorghum": "Sorgho", "Sorghum (imported)": "Sorgho importé",
    "Maize (local)": "Maïs local", "Maize (imported)": "Maïs importé",
    "Beans (niebe)": "Niébé (haricot)", "Groundnuts (shelled)": "Arachide décortiquée",
    "Groundnuts (unshelled)": "Arachide en coque",
}
REGION_FR = {"Saint Louis": "Saint-Louis", "Thies": "Thiès",
             "Kedougou": "Kédougou", "Sedhiou": "Sédhiou"}
print("Racine projet :", PROJ)
"""

# ===========================================================================
# NOTEBOOK 01 — ACQUISITION & NETTOYAGE
# ===========================================================================
nb01 = [
("md", """# 01 — Acquisition & nettoyage des données réelles
## Prix des céréales & légumineuses au Sénégal — WFP & Banque mondiale (2007–2026)

**100 % données réelles et officielles :**
- 🥗 **WFP / HDX** — prix de marché *réels* (relevés `actual`, *Retail*, KG),
  mensuels, **64 marchés**, **14 régions**, depuis 2000.
  → [data.humdata.org/dataset/wfp-food-prices-for-senegal](https://data.humdata.org/dataset/wfp-food-prices-for-senegal)
- 🌍 **Banque mondiale (API)** — inflation officielle, PIB/hab., population,
  production alimentaire, etc.
- 🗺️ **geoBoundaries** — contours des 14 régions.

> ⚙️ Les fichiers sont d'abord téléchargés par `scripts/download_data.py`.
> Ce notebook les nettoie et produit un modèle en étoile dans `data/processed/`.
"""),
("code", SETUP),
("md", "### 1. Chargement des données brutes (la 2ᵉ ligne du CSV WFP contient les balises HXL → ignorée)"),
("code", r"""
prix = pd.read_csv(os.path.join(RAW, "wfp_food_prices_sen.csv"), skiprows=[1])
marches = pd.read_csv(os.path.join(RAW, "wfp_markets_sen.csv"), skiprows=[1])
wb = pd.read_csv(os.path.join(RAW, "worldbank_senegal.csv"))
print("Prix bruts :", prix.shape)
print("Période    :", prix["date"].min(), "->", prix["date"].max())
print("Colonnes   :", list(prix.columns))
prix.head(3)
"""),
("md", "### 2. Diagnostic qualité"),
("code", r"""
print("Valeurs manquantes :\n", prix[["date","admin1","commodity","price"]].isna().sum().to_dict())
print("\npriceflag :", prix["priceflag"].value_counts().to_dict())
print("pricetype :", prix["pricetype"].value_counts().to_dict())
print("unités    :", prix["unit"].value_counts().to_dict())
print("devises   :", prix["currency"].value_counts().to_dict())
print("\nRelevés par an :")
print(prix.assign(an=pd.to_datetime(prix['date']).dt.year).groupby("an").size().loc[[2000,2006,2007,2015,2024,2026]].to_dict())
"""),
("md", """### 3. Nettoyage
- Conversion des dates au 1er du mois.
- Filtres : `actual`, *Retail*, unité KG, prix > 0.
- Libellés FR ; on **restreint à partir de 2007** (couverture fiable : ~52 marchés).
- Suppression des doublons."""),
("code", r"""
p = prix.copy()
p["date"] = pd.to_datetime(p["date"]).values.astype("datetime64[M]")
p = p[(p["priceflag"] == "actual") & (p["pricetype"] == "Retail") & (p["unit"] == "KG")]
p = p[p["price"] > 0].dropna(subset=["price", "commodity", "admin1"])
p["commodity_fr"] = p["commodity"].map(COMMOD_FR).fillna(p["commodity"])
p["region"] = p["admin1"]                       # nom brut (jointure GeoJSON)
p["region_fr"] = p["region"].replace(REGION_FR) # nom d'affichage
p = p[p["date"] >= "2007-01-01"]
n0 = len(p)
p = p.drop_duplicates(subset=["date", "market", "commodity_fr"])
print(f"Lignes retenues : {len(p):,} (doublons retirés : {n0-len(p):,})")
print("Denrées :", sorted(p["commodity_fr"].unique()))
print("Régions :", sorted(p["region_fr"].unique()))
"""),
("md", """### 4. Agrégation : prix national & régional (médiane robuste entre marchés)"""),
("code", r"""
# National : médiane des marchés par mois et denrée
fact_nat = (p.groupby(["date", "commodity_fr"])
              .agg(prix_median=("price", "median"),
                   prix_moyen=("price", "mean"),
                   nb_marches=("market", "nunique"))
              .reset_index())
# Régional
fact_reg = (p.groupby(["date", "region", "region_fr", "commodity_fr"])
              .agg(prix_median=("price", "median"),
                   nb_marches=("market", "nunique"))
              .reset_index())
# Lissage des valeurs aberrantes isolées (médiane glissante robuste / MAD)
def winsorize_group(g):
    med = g.rolling(13, center=True, min_periods=4).median()
    mad = (g - med).abs().rolling(13, center=True, min_periods=4).median()
    out = g.copy(); m = (g - med).abs() > 3.5 * mad.replace(0, np.nan)
    out[m] = med[m]; return out
fact_nat = fact_nat.sort_values(["commodity_fr", "date"])
n_out = 0
for c, gg in fact_nat.groupby("commodity_fr"):
    w_ = winsorize_group(gg["prix_median"]); n_out += int((w_ != gg["prix_median"]).sum())
    fact_nat.loc[gg.index, "prix_median"] = w_.values
print(f"fact national : {fact_nat.shape} | fact régional : {fact_reg.shape} "
      f"| points aberrants lissés : {n_out}")
fact_nat.tail(3)
"""),
("md", """### 5. Indice du panier céréalier (base 100 = 2015)
Panier pondéré reflétant le régime alimentaire sénégalais :
**riz importé 40 %, mil 25 %, maïs local 15 %, riz local 10 %, sorgho 10 %**.
Indice = moyenne pondérée des prix relatifs (prix / prix moyen de 2015)."""),
("code", r"""
PANIER = {"Riz importé (brisé)": 0.40, "Mil": 0.25, "Maïs local": 0.15,
          "Riz local": 0.10, "Sorgho": 0.10}
piv = (fact_nat[fact_nat["commodity_fr"].isin(PANIER)]
       .pivot(index="date", columns="commodity_fr", values="prix_median")
       .asfreq("MS").interpolate(limit=3))
base = piv.loc["2015"].mean()                      # prix moyen 2015 par denrée
rel = piv.divide(base, axis=1) * 100               # prix relatifs (base 100=2015)
w = pd.Series(PANIER)
indice = (rel[w.index] * w).sum(axis=1) / w.sum()
panier_nat = pd.DataFrame({"date": indice.index, "indice_panier": indice.values})
panier_nat["var_annuelle_pct"] = panier_nat["indice_panier"].pct_change(12) * 100
print("Indice panier — base 2015≈100 :", round(panier_nat.set_index('date').loc['2015','indice_panier'].mean(),1))
print("Dernier indice :", round(panier_nat['indice_panier'].iloc[-1],1),
      "(", panier_nat['date'].iloc[-1].strftime('%b %Y'), ")")
panier_nat.tail(3)
"""),
("md", "### 6. Inflation alimentaire WFP vs inflation officielle (Banque mondiale)"),
("code", r"""
panier_nat["annee"] = panier_nat["date"].dt.year
wfp_an = panier_nat.dropna(subset=["var_annuelle_pct"]).groupby("annee")["var_annuelle_pct"].mean()
wb_infl = wb[wb["code"] == "FP.CPI.TOTL.ZG"].set_index("annee")["valeur"]
comp = pd.DataFrame({"inflation_alimentaire_WFP_%": wfp_an.round(1),
                     "inflation_officielle_BM_%": wb_infl.round(1)}).dropna()
print(comp.loc[2008:].to_string())
print("\nCorrélation WFP vs officielle :",
      round(comp["inflation_alimentaire_WFP_%"].corr(comp["inflation_officielle_BM_%"]), 2))
"""),
("md", "### 7. Prix réels (déflatés par l'IPC officiel) + indicateurs macro"),
("code", r"""
cpi = wb[wb["code"] == "FP.CPI.TOTL"][["annee", "valeur"]].rename(columns={"valeur": "cpi"})
fact_nat["annee"] = fact_nat["date"].dt.year
fact_nat = fact_nat.merge(cpi, on="annee", how="left")
fact_nat["cpi"] = fact_nat["cpi"].ffill().bfill()
fact_nat["prix_reel_2010"] = fact_nat["prix_median"] / fact_nat["cpi"] * 100
# Variation annuelle par denrée
fact_nat = fact_nat.sort_values(["commodity_fr", "date"])
fact_nat["var_annuelle_pct"] = (fact_nat.groupby("commodity_fr")["prix_median"]
                                .pct_change(12) * 100)
# WB en format large (1 colonne par indicateur)
wb_wide = wb.pivot(index="annee", columns="code", values="valeur").reset_index()
fact_nat.tail(2)
"""),
("md", "### 8. Dimensions + référentiel géographique des marchés"),
("code", r"""
dim_commodity = (p.groupby(["commodity_fr", "category"]).size().reset_index(name="n_releves")
                   .assign(dans_panier=lambda d: d["commodity_fr"].isin(PANIER)))
dim_region = (p.groupby(["region", "region_fr"])["market"].nunique()
                .reset_index(name="nb_marches"))
# Référentiel marchés (coordonnées GPS réelles)
markets_geo = (p.groupby(["market", "region", "region_fr"])
                 .agg(latitude=("latitude", "first"), longitude=("longitude", "first"),
                      n_releves=("price", "size"),
                      dernier_releve=("date", "max"))
                 .reset_index())
print("Denrées :", len(dim_commodity), "| Régions :", len(dim_region),
      "| Marchés géolocalisés :", len(markets_geo))
markets_geo.head(3)
"""),
("md", "### 9. Indice panier régional (base 100 = 2015) pour la carte"),
("code", r"""
reg_rows = []
for reg, g in fact_reg[fact_reg["commodity_fr"].isin(PANIER)].groupby("region"):
    pv = g.pivot_table(index="date", columns="commodity_fr", values="prix_median").asfreq("MS").interpolate(limit=3)
    if "2015" not in pv.index.strftime("%Y"):
        continue
    b = pv.loc["2015"].mean()
    if b.isna().all():
        continue
    rl = pv.divide(b, axis=1) * 100
    cols = [c for c in w.index if c in rl.columns]
    idx = (rl[cols] * w[cols]).sum(axis=1) / w[cols].sum()
    tmp = pd.DataFrame({"date": idx.index, "region": reg, "indice_panier": idx.values})
    reg_rows.append(tmp)
panier_reg = pd.concat(reg_rows, ignore_index=True)
panier_reg["region_fr"] = panier_reg["region"].replace(REGION_FR)
panier_reg["var_annuelle_pct"] = (panier_reg.sort_values("date")
                                  .groupby("region")["indice_panier"].pct_change(12) * 100)
print("Indice régional :", panier_reg.shape, "| régions :", panier_reg["region"].nunique())
"""),
("md", "### 10. Écriture du modèle en étoile dans `data/processed/`"),
("code", r"""
tables = {
    "fact_prix_national": fact_nat, "fact_prix_regional": fact_reg,
    "indice_panier_national": panier_nat, "indice_panier_regional": panier_reg,
    "dim_commodity": dim_commodity, "dim_region": dim_region,
    "markets_geo": markets_geo, "worldbank": wb_wide, "inflation_compare": comp.reset_index(),
}
for name, df in tables.items():
    df.to_csv(os.path.join(PROC, f"{name}.csv"), index=False, encoding="utf-8-sig")
    print(f"  {name:24s} {df.shape}")
print("\n✅ Données réelles nettoyées et structurées.")
"""),
]

# ===========================================================================
# NOTEBOOK 02 — EDA
# ===========================================================================
nb02 = [
("md", """# 02 — Analyse exploratoire (données réelles)
## Prix des céréales & légumineuses au Sénégal (2007–2026)

Questions : Comment ont évolué les prix réels des céréales ? Quels chocs
(2008, 2022) ? Quelles régions/denrées les plus touchées ? L'inflation
alimentaire suit-elle l'inflation officielle ?"""),
("code", SETUP),
("code", r"""
fact_nat = pd.read_csv(os.path.join(PROC, "fact_prix_national.csv"), parse_dates=["date"])
fact_reg = pd.read_csv(os.path.join(PROC, "fact_prix_regional.csv"), parse_dates=["date"])
panier = pd.read_csv(os.path.join(PROC, "indice_panier_national.csv"), parse_dates=["date"])
panier_reg = pd.read_csv(os.path.join(PROC, "indice_panier_regional.csv"), parse_dates=["date"])
markets = pd.read_csv(os.path.join(PROC, "markets_geo.csv"))
comp = pd.read_csv(os.path.join(PROC, "inflation_compare.csv"))
wb = pd.read_csv(os.path.join(PROC, "worldbank.csv"))
print("OK")
"""),
("md", "### 1. Évolution des prix nominaux des principales céréales (FCFA/kg)"),
("code", r"""
key = ["Riz importé (brisé)", "Mil", "Maïs local", "Sorgho", "Riz local"]
fig, ax = plt.subplots()
for c in key:
    g = fact_nat[fact_nat["commodity_fr"] == c].sort_values("date")
    ax.plot(g["date"], g["prix_median"], lw=1.5, label=c)
for yr, txt in [(2008, "Crise 2008"), (2022, "Choc 2022")]:
    ax.axvspan(pd.Timestamp(yr,1,1), pd.Timestamp(yr,12,31), color="grey", alpha=.12)
ax.legend(ncol=3, fontsize=8); ax.set_ylabel("Prix médian (FCFA/kg)")
ax.set_title("Prix de détail des céréales de base au Sénégal (réel, WFP)")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "01_prix_cereales.png"), bbox_inches="tight")
plt.close(fig); print("→ 01_prix_cereales.png")
"""),
("md", "### 2. Indice du panier céréalier & inflation alimentaire en glissement annuel"),
("code", r"""
fig, ax1 = plt.subplots()
ax1.plot(panier["date"], panier["indice_panier"], color="#1f4e79", lw=2, label="Indice panier (100=2015)")
ax1.set_ylabel("Indice (base 100 = 2015)", color="#1f4e79")
ax2 = ax1.twinx()
ax2.plot(panier["date"], panier["var_annuelle_pct"], color="#c0392b", lw=1.4)
ax2.axhline(0, color="grey", lw=.6); ax2.set_ylabel("Inflation alimentaire a/a (%)", color="#c0392b")
ax1.set_title("Indice du panier céréalier et inflation alimentaire")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "02_indice_panier.png"), bbox_inches="tight")
plt.close(fig); print("→ 02_indice_panier.png")
"""),
("md", "### 3. Inflation alimentaire (WFP) vs inflation officielle (Banque mondiale)"),
("code", r"""
c = comp.dropna()
fig, ax = plt.subplots()
ax.plot(c["annee"], c["inflation_alimentaire_WFP_%"], "-o", color="#27ae60", label="Alimentaire (WFP)")
ax.plot(c["annee"], c["inflation_officielle_BM_%"], "-o", color="#1f4e79", label="Officielle (Banque mondiale)")
ax.axhline(0, color="grey", lw=.6); ax.legend(); ax.set_ylabel("%")
ax.set_title("Inflation alimentaire vs inflation officielle au Sénégal")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "03_wfp_vs_officiel.png"), bbox_inches="tight")
plt.close(fig); print("→ 03_wfp_vs_officiel.png  | corr =",
      round(c["inflation_alimentaire_WFP_%"].corr(c["inflation_officielle_BM_%"]), 2))
"""),
("md", "### 4. Hausse cumulée par denrée (2007 → 2026) et volatilité"),
("code", r"""
g = fact_nat.sort_values("date")
deb = g.groupby("commodity_fr").first()["prix_median"]
fin = g.groupby("commodity_fr").last()["prix_median"]
hausse = ((fin/deb - 1)*100).dropna().sort_values(ascending=False)
fig, ax = plt.subplots(figsize=(10,6))
ax.barh(hausse.index[::-1], hausse.values[::-1], color=sns.color_palette("flare", len(hausse)))
for i,v in enumerate(hausse.values[::-1]):
    ax.text(v+2, i, f"{v:.0f}%", va="center", fontsize=8)
ax.set_title("Hausse cumulée des prix par denrée (2007 → 2026)"); ax.set_xlabel("%")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "04_hausse_denrees.png"), bbox_inches="tight")
plt.close(fig); print("→ 04_hausse_denrees.png")
"""),
("md", "### 5. Comparaison régionale — prix médian du riz importé par région (heatmap)"),
("code", r"""
riz = fact_reg[fact_reg["commodity_fr"] == "Riz importé (brisé)"].copy()
riz["annee"] = riz["date"].dt.year
piv = riz.pivot_table(index="region_fr", columns="annee", values="prix_median", aggfunc="median")
piv = piv.loc[:, piv.columns >= 2010]
fig, ax = plt.subplots(figsize=(13,6))
sns.heatmap(piv, cmap="YlOrRd", annot=False, cbar_kws={"label":"FCFA/kg"}, ax=ax)
ax.set_title("Prix médian du riz importé par région et par année"); ax.set_xlabel(""); ax.set_ylabel("")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "05_heatmap_riz_region.png"), bbox_inches="tight")
plt.close(fig); print("→ 05_heatmap_riz_region.png")
"""),
("md", "### 6. Saisonnalité — profil mensuel moyen (soudure)"),
("code", r"""
mil = fact_nat[fact_nat["commodity_fr"].isin(["Mil","Sorgho","Maïs local"])].copy()
mil["mois"] = mil["date"].dt.month
# indice saisonnier = prix / moyenne annuelle de la denrée
mil["an"] = mil["date"].dt.year
mil = mil.merge(mil.groupby(["commodity_fr","an"])["prix_median"].mean().rename("moy_an"),
                on=["commodity_fr","an"])
mil["saison"] = mil["prix_median"]/mil["moy_an"]*100
prof = mil.groupby(["commodity_fr","mois"])["saison"].mean().reset_index()
fig, ax = plt.subplots()
for c,gg in prof.groupby("commodity_fr"):
    ax.plot(gg["mois"], gg["saison"], "-o", label=c, lw=1.5)
ax.axhline(100, color="grey", lw=.6); ax.legend()
ax.set_xticks(range(1,13)); ax.set_xlabel("Mois"); ax.set_ylabel("Indice saisonnier (moy. an = 100)")
ax.set_title("Saisonnalité des céréales locales (pic en période de soudure)")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "06_saisonnalite.png"), bbox_inches="tight")
plt.close(fig); print("→ 06_saisonnalite.png")
"""),
("md", "### 7. Carte des marchés (coordonnées GPS réelles) + choroplèthe régionale"),
("code", r"""
from matplotlib.patches import Polygon as MplPoly
import matplotlib.colors as mcolors, matplotlib.cm as cm
geo = json.load(open(os.path.join(GEO, "senegal_regions.geojson"), encoding="utf-8"))
def rings(g): return [g["coordinates"]] if g["type"]=="Polygon" else g["coordinates"]

# indice panier régional récent (12 derniers mois)
last = pd.to_datetime(panier_reg["date"]).max()
recent = panier_reg[pd.to_datetime(panier_reg["date"]) > last - pd.DateOffset(months=12)]
val_reg = recent.groupby("region")["indice_panier"].mean().to_dict()

fig, ax = plt.subplots(figsize=(10,8))
vals=[v for v in val_reg.values()]; norm=mcolors.Normalize(min(vals),max(vals))
sm=cm.ScalarMappable(cmap="YlOrRd",norm=norm); sm.set_array([])
for feat in geo["features"]:
    name=feat["properties"]["shapeName"]; val=val_reg.get(name)
    color=sm.to_rgba(val) if val is not None else "#eeeeee"
    for poly in rings(feat["geometry"]):
        ax.add_patch(MplPoly(np.array(poly[0]), closed=True, facecolor=color, edgecolor="white", lw=.6))
# marchés réels
ax.scatter(markets["longitude"], markets["latitude"], s=18, c="#1f4e79",
           edgecolor="white", linewidth=.4, zorder=5, label="Marchés WFP (64)")
ax.autoscale(); ax.set_aspect("equal"); ax.axis("off"); ax.legend(loc="lower left")
ax.set_title("Indice panier céréalier par région + marchés relevés (réel)")
cbar=fig.colorbar(sm,ax=ax,shrink=.5); cbar.set_label("Indice panier (100=2015)")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "07_carte_marches.png"), bbox_inches="tight", dpi=120)
plt.close(fig); print("→ 07_carte_marches.png")
"""),
("md", "### 8. Contexte macro (Banque mondiale) — PIB/hab. & production alimentaire vs prix"),
("code", r"""
wbx = wb.copy()
fig, ax1 = plt.subplots()
ax1.plot(panier["date"], panier["indice_panier"], color="#c0392b", lw=2, label="Indice panier céréales")
ax1.set_ylabel("Indice panier (100=2015)", color="#c0392b")
ax2 = ax1.twinx()
if "AG.PRD.FOOD.XD" in wbx.columns:
    ax2.plot(pd.to_datetime(wbx["annee"], format="%Y"), wbx["AG.PRD.FOOD.XD"],
             color="#27ae60", lw=1.8, marker="o", ms=3, label="Prod. alimentaire (BM)")
    ax2.set_ylabel("Indice production alim. (2014-16=100)", color="#27ae60")
ax1.set_title("Prix du panier céréalier vs production alimentaire")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "08_macro_contexte.png"), bbox_inches="tight")
plt.close(fig); print("→ 08_macro_contexte.png")
"""),
("md", """### Synthèse EDA
- Les prix des céréales montrent deux chocs majeurs **réels** : la **crise
  alimentaire de 2008** et le **choc de 2022** (guerre en Ukraine, prix mondiaux).
- L'**inflation alimentaire (WFP)** est nettement corrélée à l'**inflation
  officielle (Banque mondiale)**, ce qui valide la cohérence des données.
- Forte **saisonnalité** des céréales locales (mil, sorgho) : pic en période de
  soudure (avant récoltes).
- Disparités régionales marquées, lisibles sur la carte des 64 marchés réels.
"""),
]

# ===========================================================================
# NOTEBOOK 03 — FORECASTING
# ===========================================================================
nb03 = [
("md", """# 03 — Prévision des prix (données réelles)
On prévoit le **prix du riz importé** (denrée la mieux couverte) et l'**indice
du panier céréalier** sur 12 mois, en comparant plusieurs modèles."""),
("code", SETUP),
("code", r"""
fact_nat = pd.read_csv(os.path.join(PROC, "fact_prix_national.csv"), parse_dates=["date"])
panier = pd.read_csv(os.path.join(PROC, "indice_panier_national.csv"), parse_dates=["date"])

riz = (fact_nat[fact_nat["commodity_fr"] == "Riz importé (brisé)"]
       .set_index("date")["prix_median"].asfreq("MS").interpolate(limit=4)).dropna()
serie = riz.copy()
print("Série riz importé :", serie.index.min().date(), "->", serie.index.max().date(),
      "|", len(serie), "points")
H = 12
train, test = serie.iloc[:-H], serie.iloc[-H:]
def metrics(y, yhat):
    y, yhat = np.asarray(y), np.asarray(yhat)
    return (float(np.sqrt(np.mean((y-yhat)**2))), float(np.mean(np.abs(y-yhat))),
            float(np.mean(np.abs((y-yhat)/y))*100))
"""),
("md", "### 1. Baselines + régression + SARIMA"),
("code", r"""
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.statespace.sarimax import SARIMAX

snaive = train.iloc[-12:].values[:len(test)]
res_sn = metrics(test.values, snaive)

t = np.arange(len(serie))
M = pd.get_dummies(serie.index.month, prefix="m", drop_first=True).reset_index(drop=True)
X = pd.concat([pd.Series(t, name="t"), M], axis=1)
lr = LinearRegression().fit(X.iloc[:-H], train.values)
res_lr = metrics(test.values, lr.predict(X.iloc[-H:]))

sar = SARIMAX(train, order=(1,1,1), seasonal_order=(1,1,0,12),
              enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
res_sar = metrics(test.values, sar.forecast(H).values)
print("Seasonal naive RMSE=%.1f MAE=%.1f MAPE=%.2f%%" % res_sn)
print("Régression lin. RMSE=%.1f MAE=%.1f MAPE=%.2f%%" % res_lr)
print("SARIMA         RMSE=%.1f MAE=%.1f MAPE=%.2f%%" % res_sar)
"""),
("md", "### 2. Prophet (si la toolchain Stan est disponible)"),
("code", r"""
def _prep_prophet():
    import sys, glob
    if not sys.platform.startswith("win"): return
    cands = [r"C:\rtools44\usr\bin", r"C:\Program Files\Git\mingw64\bin"]
    cands += glob.glob(os.path.join(os.path.dirname(os.__file__), "..", "site-packages",
             "prophet", "stan_model", "cmdstan-*", "stan", "lib", "stan_math", "lib", "tbb"))
    for d in cands:
        if os.path.isdir(d):
            try: os.add_dll_directory(d)
            except Exception: pass
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
res_prophet = None
try:
    _prep_prophet()
    from prophet import Prophet
    dfp = train.reset_index(); dfp.columns = ["ds", "y"]
    m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    m.fit(dfp)
    fc = m.predict(m.make_future_dataframe(periods=H, freq="MS")).set_index("ds")["yhat"].iloc[-H:]
    res_prophet = metrics(test.values, fc.values)
    print("Prophet        RMSE=%.1f MAE=%.1f MAPE=%.2f%%" % res_prophet)
except Exception as e:
    print("⚠️ Prophet intégré mais backend Stan non exécutable ici (%s)." % type(e).__name__)
    print("   -> conda-forge `prophet` ou RTools pour l'activer.")
"""),
("md", "### 3. Comparaison & sélection"),
("code", r"""
rows = [("Seasonal naive", *res_sn), ("Régression linéaire", *res_lr), ("SARIMA", *res_sar)]
if res_prophet: rows.append(("Prophet", *res_prophet))
comp = pd.DataFrame(rows, columns=["modele","RMSE","MAE","MAPE_%"]).sort_values("RMSE")
comp.to_csv(os.path.join(MODELS, "model_comparison.csv"), index=False, encoding="utf-8-sig")
print(comp.to_string(index=False)); print("\nMeilleur :", comp.iloc[0]["modele"])
"""),
("md", """### 4. Prévision 12 mois (riz importé) — **modèle retenu = meilleur RMSE**
On réentraîne le modèle gagnant sur toute la série. Les intervalles proviennent
du modèle SARIMA, ou des résidus du modèle linéaire le cas échéant."""),
("code", r"""
BEST = comp.iloc[0]["modele"]
future_idx = pd.date_range(serie.index[-1] + pd.offsets.MonthBegin(1), periods=H, freq="MS")

def forecast_with(best, serie, H, future_idx):
    if best == "SARIMA":
        m = SARIMAX(serie, order=(1,1,1), seasonal_order=(1,1,0,12),
                    enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
        f = m.get_forecast(H); ci = f.conf_int(alpha=0.2)
        return f.predicted_mean.values, ci.iloc[:,0].values, ci.iloc[:,1].values
    if best == "Régression linéaire":
        n = len(serie); t = np.arange(n)
        Mf = pd.get_dummies(serie.index.month, prefix="m", drop_first=True).reset_index(drop=True)
        Xf = pd.concat([pd.Series(t, name="t"), Mf], axis=1)
        lr = LinearRegression().fit(Xf, serie.values)
        resid_std = (serie.values - lr.predict(Xf)).std()
        tf = np.arange(n, n+H)
        Mp = pd.get_dummies(future_idx.month, prefix="m", drop_first=True).reindex(
             columns=Mf.columns, fill_value=0).reset_index(drop=True)
        Xp = pd.concat([pd.Series(tf, name="t"), Mp], axis=1)
        mean = lr.predict(Xp)
        return mean, mean - 1.28*resid_std, mean + 1.28*resid_std
    # Seasonal naive
    last12 = serie.iloc[-12:].values
    mean = np.resize(last12, H)
    sd = np.std(np.diff(serie.values[::12])) if len(serie) > 24 else serie.std()
    return mean, mean - 1.28*sd, mean + 1.28*sd

mean, bas, haut = forecast_with(BEST, serie, H, future_idx)
fc = pd.DataFrame({"date": future_idx, "prix_prevu": mean, "bas": bas, "haut": haut})
fc.to_csv(os.path.join(MODELS, "forecast_riz.csv"), index=False, encoding="utf-8-sig")
fig, ax = plt.subplots()
ax.plot(serie.index, serie.values, color="#1f4e79", lw=1.6, label="Historique")
ax.plot(fc["date"], fc["prix_prevu"], color="#c0392b", lw=2, label=f"Prévision ({BEST})")
ax.fill_between(fc["date"], fc["bas"], fc["haut"], color="#c0392b", alpha=.15, label="IC 80%")
ax.legend(); ax.set_ylabel("FCFA/kg")
ax.set_title(f"Prévision du prix du riz importé (12 mois) — {BEST}")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "09_forecast_riz.png"), bbox_inches="tight")
plt.close(fig)
print("Modèle retenu : %s | prix actuel %.0f -> prévu %.0f FCFA/kg"
      % (BEST, serie.iloc[-1], fc["prix_prevu"].iloc[-1]))
"""),
("md", "### 5. Prévision de l'indice du panier céréalier"),
("code", r"""
ip = panier.set_index("date")["indice_panier"].asfreq("MS").interpolate(limit=3).dropna()
mp = SARIMAX(ip, order=(1,1,1), seasonal_order=(1,1,0,12),
             enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
ff = mp.get_forecast(H); pm=ff.predicted_mean; pci=ff.conf_int(alpha=0.2)
pf = pd.DataFrame({"date":pm.index, "indice_prevu":pm.values,
                   "bas":pci.iloc[:,0].values, "haut":pci.iloc[:,1].values})
ext = pd.concat([ip, pm])
pf["inflation_prevue_pct"] = [(ext.loc[d]/ext.loc[d-pd.DateOffset(years=1)]-1)*100 for d in pm.index]
pf.to_csv(os.path.join(MODELS, "forecast_panier.csv"), index=False, encoding="utf-8-sig")
fig, ax = plt.subplots()
ax.plot(ip.index, ip.values, color="#1f4e79", lw=1.6, label="Historique")
ax.plot(pf["date"], pf["indice_prevu"], color="#c0392b", lw=2, label="Prévision")
ax.fill_between(pf["date"], pf["bas"], pf["haut"], color="#c0392b", alpha=.15)
ax.legend(); ax.set_ylabel("Indice (100=2015)"); ax.set_title("Prévision de l'indice du panier céréalier")
fig.tight_layout(); fig.savefig(os.path.join(FIG, "10_forecast_panier.png"), bbox_inches="tight")
plt.close(fig)
print("→ 10_forecast_panier.png | inflation alimentaire prévue ~%.1f%%"
      % pf["inflation_prevue_pct"].mean())
"""),
("md", """### Conclusion
- **SARIMA** capture tendance + saisonnalité des prix céréaliers réels.
- Prévision à interpréter avec prudence : sensible aux chocs exogènes (prix
  mondiaux, climat/récoltes, politiques de subvention).
"""),
]

build(os.path.join(NB_DIR, "01_acquisition_nettoyage.ipynb"), nb01)
build(os.path.join(NB_DIR, "02_analyse_exploratoire.ipynb"), nb02)
build(os.path.join(NB_DIR, "03_prevision_forecasting.ipynb"), nb03)
print("Notebooks construits.")
