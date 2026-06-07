-- =====================================================================
-- Requêtes analytiques — Prix des céréales & inflation au Sénégal
-- =====================================================================

-- 1. Prix moyen national par denrée et par année
SELECT commodity_fr, annee, ROUND(AVG(prix_median),1) AS prix_moyen_fcfa_kg
FROM fact_prix_national
GROUP BY commodity_fr, annee
ORDER BY commodity_fr, annee;

-- 2. Hausse cumulée des prix par denrée (premier vs dernier relevé)
WITH bornes AS (
  SELECT commodity_fr,
         FIRST_VALUE(prix_median) OVER (PARTITION BY commodity_fr ORDER BY date) AS p_debut,
         FIRST_VALUE(prix_median) OVER (PARTITION BY commodity_fr ORDER BY date DESC) AS p_fin
  FROM fact_prix_national
)
SELECT commodity_fr,
       ROUND((p_fin/p_debut - 1)*100,1) AS hausse_cumulee_pct
FROM bornes GROUP BY commodity_fr, p_debut, p_fin
ORDER BY hausse_cumulee_pct DESC;

-- 3. Inflation alimentaire annuelle (glissement annuel de l'indice panier)
SELECT annee, ROUND(AVG(var_annuelle_pct),1) AS inflation_alimentaire_pct
FROM indice_panier_national
WHERE var_annuelle_pct IS NOT NULL
GROUP BY annee ORDER BY annee;

-- 4. Comparaison inflation alimentaire (WFP) vs officielle (Banque mondiale)
SELECT p.annee,
       ROUND(AVG(p.var_annuelle_pct),1) AS infl_alimentaire_wfp,
       MAX(w."FP.CPI.TOTL.ZG")          AS infl_officielle_bm
FROM indice_panier_national p
JOIN worldbank w ON w.annee = p.annee
WHERE p.var_annuelle_pct IS NOT NULL
GROUP BY p.annee ORDER BY p.annee;

-- 5. Top 5 régions les plus chères (prix médian du riz importé, dernière année)
SELECT region_fr, ROUND(AVG(prix_median),1) AS prix_riz_fcfa_kg
FROM fact_prix_regional
WHERE commodity_fr = 'Riz importé (brisé)'
  AND EXTRACT(YEAR FROM date) = (SELECT MAX(EXTRACT(YEAR FROM date)) FROM fact_prix_regional)
GROUP BY region_fr ORDER BY prix_riz_fcfa_kg DESC LIMIT 5;

-- 6. Volatilité des prix par denrée (écart-type relatif)
SELECT commodity_fr,
       ROUND(STDDEV(prix_median)/AVG(prix_median)*100,1) AS coef_variation_pct
FROM fact_prix_national
GROUP BY commodity_fr ORDER BY coef_variation_pct DESC;

-- 7. Profil saisonnier : prix moyen du mil par mois (indice base moyenne annuelle)
SELECT EXTRACT(MONTH FROM date) AS mois,
       ROUND(AVG(prix_median),1) AS prix_moyen_mil
FROM fact_prix_national
WHERE commodity_fr = 'Mil'
GROUP BY mois ORDER BY mois;

-- 8. Pic d'inflation alimentaire (mois le plus inflationniste)
SELECT date, ROUND(var_annuelle_pct,1) AS inflation_pct
FROM indice_panier_national
ORDER BY var_annuelle_pct DESC NULLS LAST LIMIT 5;

-- 9. Couverture des relevés : nombre de marchés actifs par an
SELECT EXTRACT(YEAR FROM date) AS annee, COUNT(DISTINCT region) AS regions,
       ROUND(AVG(nb_marches),1) AS marches_moyen_par_releve
FROM fact_prix_regional GROUP BY annee ORDER BY annee;

-- 10. Prix réel (déflaté) vs nominal du riz importé — érosion/évolution réelle
SELECT annee,
       ROUND(AVG(prix_median),1)     AS prix_nominal,
       ROUND(AVG(prix_reel_2010),1)  AS prix_reel_base2010
FROM fact_prix_national
WHERE commodity_fr = 'Riz importé (brisé)'
GROUP BY annee ORDER BY annee;
