# -*- coding: utf-8 -*-
"""
download_data.py — Téléchargement des DONNÉES RÉELLES du projet.

Sources officielles :
  1. WFP / HDX  — prix de marché réels des denrées (Sénégal), mensuel 2000→2026.
     https://data.humdata.org/dataset/wfp-food-prices-for-senegal
  2. Banque mondiale (API v2) — indicateurs macro (inflation, PIB, population…).
     https://api.worldbank.org/v2/country/SEN/indicator/...
  3. geoBoundaries — contours des 14 régions du Sénégal (GeoJSON).

Tout est écrit dans data/raw/ et data/geo/. 100 % reproductible.
"""
import os, io, json, time, urllib.request
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
GEO = os.path.join(BASE, "data", "geo")
os.makedirs(RAW, exist_ok=True); os.makedirs(GEO, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (portfolio data project)"}

def fetch(url, dest, binary=False, retries=3):
    for k in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                content = r.read()
            mode = "wb" if binary else "wb"
            with open(dest, mode) as f:
                f.write(content)
            print(f"  ✓ {os.path.basename(dest)} ({len(content):,} octets)")
            return content
        except Exception as e:
            print(f"  … tentative {k+1} échouée ({e}); nouvelle tentative")
            time.sleep(2)
    raise RuntimeError(f"Échec du téléchargement : {url}")

# ---------------------------------------------------------------------------
# 1. WFP — prix de marché + référentiel des marchés
# ---------------------------------------------------------------------------
print("1) WFP Food Prices (HDX)")
HDX = "https://data.humdata.org/dataset/77b76bc7-1edd-43f6-a5e4-784498ff6aca/resource"
fetch(f"{HDX}/04ffc070-6d05-4653-a9f6-9f3f893a229e/download/wfp_food_prices_sen.csv",
      os.path.join(RAW, "wfp_food_prices_sen.csv"))
fetch(f"{HDX}/48a1e809-2a74-4952-8e35-b67f7f1552e2/download/wfp_markets_sen.csv",
      os.path.join(RAW, "wfp_markets_sen.csv"))

# ---------------------------------------------------------------------------
# 2. Banque mondiale — indicateurs macro (API JSON)
# ---------------------------------------------------------------------------
print("2) Banque mondiale (API)")
INDICATEURS = {
    "FP.CPI.TOTL.ZG":  "Inflation, prix à la consommation (% annuel)",
    "FP.CPI.TOTL":     "Indice des prix à la consommation (2010=100)",
    "NY.GDP.PCAP.CD":  "PIB par habitant (USD courants)",
    "NY.GDP.MKTP.KD.ZG":"Croissance du PIB (% annuel)",
    "AG.PRD.FOOD.XD":  "Indice de production alimentaire (2014-2016=100)",
    "SP.POP.TOTL":     "Population totale",
    "SL.UEM.TOTL.ZS":  "Chômage (% population active)",
    "SI.POV.DDAY":     "Pauvreté à 2,15 $/jour (% population)",
}
rows = []
for code, label in INDICATEURS.items():
    url = f"https://api.worldbank.org/v2/country/SEN/indicator/{code}?format=json&per_page=500"
    raw = fetch(url, os.path.join(RAW, f"_wb_{code}.json"))
    data = json.loads(raw)
    if len(data) < 2 or data[1] is None:
        print(f"    (pas de données pour {code})"); continue
    for obs in data[1]:
        if obs["value"] is not None:
            rows.append({"code": code, "indicateur": label,
                         "annee": int(obs["date"]), "valeur": float(obs["value"])})
    os.remove(os.path.join(RAW, f"_wb_{code}.json"))
wb = pd.DataFrame(rows).sort_values(["code", "annee"])
wb.to_csv(os.path.join(RAW, "worldbank_senegal.csv"), index=False, encoding="utf-8-sig")
print(f"  ✓ worldbank_senegal.csv ({len(wb)} observations, {wb['code'].nunique()} indicateurs)")

# ---------------------------------------------------------------------------
# 3. GeoJSON des régions
# ---------------------------------------------------------------------------
print("3) GeoJSON régions (geoBoundaries)")
fetch("https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/gbOpen/SEN/ADM1/geoBoundaries-SEN-ADM1.geojson",
      os.path.join(GEO, "senegal_regions.geojson"), binary=True)

print("\n✅ Téléchargement terminé. Données réelles dans data/raw/ et data/geo/.")
