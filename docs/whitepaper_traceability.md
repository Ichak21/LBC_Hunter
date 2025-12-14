# White paper traceability — LBC_HUNTER v1.0

Ce document relie les exigences du white paper aux implémentations réelles (code + config),
et décrit comment vérifier que le contrat reste respecté.

## 0. Points d’entrée

- Worker (scrape + IA + scoring + DB) : `main.py`
- UI (Streamlit multi-pages) : `dashboard.py`, `pages/*`
- Source unique de config runtime : `core/app_config.py`
- Source unique de scoring : `core/scoring_config.py`
- Contrat automatisé (invariants) : `tools/verify_contract.py`

## 1. Architecture logique (résumé)

### Flux Worker
1. Liste des recherches (`core/search_manager.py`)
2. Scraping résultats (`core/scraper.py`)
3. Enrichissement (description + IA) (`core/scraper.py` + `core/ai_analyst.py`)
4. Upsert DB (`core/db_client.py`)
5. Market analysis / S_Deal (`core/price_engine.py`)
6. Archivage annonces anciennes (`core/db_client.py`)

### Flux UI
1. Home : stats + tables + logs (`dashboard.py`, `frontend/data_loader.py`)
2. Details Searches : analyse recherche + navigation vers annonce (`pages/1_🔍_Details_Searches.py`)
3. Details Ads : fiche annonce (WIP/UX P1) (`pages/2_📄_Details_Ads.py`)
4. Searches Manager (WIP/UX P1) (`pages/3_🎛️_Searches_Manager.py`)
5. Settings (WIP/UX P1) (`pages/4_⚙️_Settings.py`)

## 2. Règles white paper → Implémentation → Paramètres → Preuves

### 2.1 Score final = score_base × (K_meca × K_modif × K_arnaque)
- Implémentation :
  - IA calcule les K (et score final) : `core/ai_analyst.py` (`_calculate_score`)
  - PriceEngine met à jour S_Deal et recalcule total : `core/price_engine.py` (`update_deal_scores`)
- Paramètres :
  - poids : `core/scoring_config.py` → `SCORING_CONFIG["weights"]`
  - base scores : `SCORING_CONFIG["base_scores"]`
  - calibration K / severity (si présent) : `SCORING_CONFIG["severity"]` (ou équivalent)
- Preuve :
  - `tools/verify_contract.py` valide la somme des weights et les bornes de config.

### 2.2 S_Deal basé sur le ratio (virtual_price / market_estimation) et configurable
- Implémentation :
  - calcul ratio + S_Deal : `core/price_engine.py` (fonction S_Deal / scoring)
- Paramètres :
  - `SCORING_CONFIG["price_engine"]["scoring"]` :
    - `good_deal_ratio`, `neutral_ratio`, `bad_deal_ratio`
- Preuve :
  - `tools/verify_contract.py` valide `good < neutral < bad`

### 2.3 Prix virtuel = prix affiché + frais chiffrables
- Implémentation :
  - IA : `core/ai_analyst.py` (virtual_price + repair_cost)
  - PriceEngine : `core/price_engine.py` (recalcule virtual_price si frais présents)
- Paramètres :
  - structure JSON `ai_analysis.frais_chiffrables[]` (contract prompt IA)

### 2.4 Robustesse Streamlit (cache, navigation, session_state)
- Implémentation :
  - cache : `frontend/data_loader.py` (`@st.cache_data(ttl=...)`)
  - TTL : `core/app_config.py` → `streamlit.cache_ttl_seconds`
  - navigation : `frontend/layout.py`, `dashboard.py`, `pages/*`
- Preuve :
  - navigation “clic recherche → details searches” et “clic annonce → details ads” fonctionne sans rerun/no-op.

### 2.5 Logs unifiés et visibles dans l’UI
- Implémentation :
  - logging : `core/logging_config.py` (`setup_logging`)
  - affichage UI : `frontend/data_loader.py` (`load_logs`)
- Paramètres :
  - `core/app_config.py` → `paths.worker_log_file`
- Preuve :
  - fichier de log rotatif présent et lisible via Home.

### 2.6 Config unique (pas de magic numbers runtime)
- Implémentation :
  - runtime config : `core/app_config.py`
  - usage : `core/scraper.py`, `main.py`, `frontend/data_loader.py`, `core/db_client.py`
- Paramètres :
  - variables d’environnement (.env / prod) :
    - `DATABASE_URL`
    - `SCRAPER_*`, `WORKER_*`, `STREAMLIT_CACHE_TTL`
    - `LOGS_DIR`, `WORKER_LOG_FILE`, `SEARCHES_DIR`

## 3. Procédure de vérification (avant merge / release)
1. Lancer :
   - `python tools/verify_contract.py`
2. Vérifier manuellement (smoke test) :
   - UI : `streamlit run dashboard.py`
   - Worker : `python main.py`
3. Vérifier logs UI :
   - section “Logs Worker” sur Home.

## 4. Hypothèses / limites connues (v1.0)
- Pages UX (Details Ads / Searches Manager / Settings) : WIP → P1
- Pas de tests unitaires systématiques en P0 (choix assumé), remplacé par contract checker + smoke tests.
