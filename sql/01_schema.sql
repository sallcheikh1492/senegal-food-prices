-- =====================================================================
-- Projet : Prix des céréales & inflation au Sénégal (données réelles WFP)
-- Schéma PostgreSQL + chargement des données traitées (data/processed/)
-- =====================================================================
DROP TABLE IF EXISTS fact_prix_national, fact_prix_regional,
    indice_panier_national, indice_panier_regional,
    dim_commodity, dim_region, markets_geo, worldbank CASCADE;

CREATE TABLE dim_commodity (
    commodity_fr  TEXT PRIMARY KEY,
    category      TEXT,
    n_releves     INTEGER,
    dans_panier   BOOLEAN
);

CREATE TABLE dim_region (
    region        TEXT PRIMARY KEY,   -- nom brut (jointure GeoJSON)
    region_fr     TEXT,
    nb_marches    INTEGER
);

CREATE TABLE markets_geo (
    market        TEXT,
    region        TEXT REFERENCES dim_region(region),
    region_fr     TEXT,
    latitude      NUMERIC,
    longitude     NUMERIC,
    n_releves     INTEGER,
    dernier_releve DATE
);

CREATE TABLE fact_prix_national (
    date          DATE,
    commodity_fr  TEXT REFERENCES dim_commodity(commodity_fr),
    prix_median   NUMERIC,
    prix_moyen    NUMERIC,
    nb_marches    INTEGER,
    annee         INTEGER,
    cpi           NUMERIC,
    prix_reel_2010 NUMERIC,
    var_annuelle_pct NUMERIC,
    PRIMARY KEY (date, commodity_fr)
);

CREATE TABLE fact_prix_regional (
    date          DATE,
    region        TEXT,
    region_fr     TEXT,
    commodity_fr  TEXT,
    prix_median   NUMERIC,
    nb_marches    INTEGER
);

CREATE TABLE indice_panier_national (
    date          DATE PRIMARY KEY,
    indice_panier NUMERIC,
    var_annuelle_pct NUMERIC,
    annee         INTEGER
);

CREATE TABLE indice_panier_regional (
    date          DATE,
    region        TEXT,
    indice_panier NUMERIC,
    region_fr     TEXT,
    var_annuelle_pct NUMERIC
);

CREATE TABLE worldbank (
    annee         INTEGER PRIMARY KEY,
    "FP.CPI.TOTL.ZG"    NUMERIC,  -- inflation (%)
    "FP.CPI.TOTL"       NUMERIC,  -- IPC (2010=100)
    "NY.GDP.PCAP.CD"    NUMERIC,  -- PIB/hab (USD)
    "NY.GDP.MKTP.KD.ZG" NUMERIC,  -- croissance PIB (%)
    "AG.PRD.FOOD.XD"    NUMERIC,  -- production alimentaire
    "SP.POP.TOTL"       NUMERIC,  -- population
    "SL.UEM.TOTL.ZS"    NUMERIC,  -- chômage (%)
    "SI.POV.DDAY"       NUMERIC   -- pauvreté 2,15$/j (%)
);

-- Chargement (psql) : adapter le chemin absolu
-- \copy dim_commodity            FROM 'data/processed/dim_commodity.csv'           CSV HEADER;
-- \copy dim_region               FROM 'data/processed/dim_region.csv'              CSV HEADER;
-- \copy markets_geo              FROM 'data/processed/markets_geo.csv'             CSV HEADER;
-- \copy fact_prix_national       FROM 'data/processed/fact_prix_national.csv'      CSV HEADER;
-- \copy fact_prix_regional       FROM 'data/processed/fact_prix_regional.csv'      CSV HEADER;
-- \copy indice_panier_national   FROM 'data/processed/indice_panier_national.csv'  CSV HEADER;
-- \copy indice_panier_regional   FROM 'data/processed/indice_panier_regional.csv'  CSV HEADER;
-- \copy worldbank                FROM 'data/processed/worldbank.csv'               CSV HEADER;
