# -*- coding: utf-8 -*-
"""Pipeline complet et reproductible : téléchargement -> notebooks -> site.
Usage : python scripts/run_all.py"""
import os, subprocess, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable

def run(cmd, cwd=BASE):
    print("\n$", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

# 1. Données réelles
run([PY, os.path.join("scripts", "download_data.py")])
# 2. (Re)construction des notebooks
run([PY, os.path.join("scripts", "_build_notebooks.py")])
# 3. Exécution des notebooks dans l'ordre
nbdir = os.path.join(BASE, "notebooks")
for nb in ["01_acquisition_nettoyage", "02_analyse_exploratoire", "03_prevision_forecasting"]:
    run([PY, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
         "--inplace", "--ExecutePreprocessor.timeout=600", nb + ".ipynb"], cwd=nbdir)
# 4. Génération du site web
run([PY, os.path.join("scripts", "build_site.py")])
print("\n✅ Pipeline terminé : data/processed, reports/figures, models, docs.")
