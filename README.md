# 🦅 LBC_Hunter

**LBC_Hunter** est une application Python d’analyse intelligente d’annonces automobiles LeBonCoin.  
Elle combine scraping, IA et scoring métier pour détecter les bonnes affaires, estimer le prix marché et identifier les risques (arnaque, modifications, fiabilité).

> ⚠️ Projet expérimental à but éducatif.  
> Non affilié à LeBonCoin.

---

## ✨ Fonctionnalités principales

- 🔎 **Scraping intelligent LeBonCoin**
  - recherches configurables (prix, année, mots-clés, whitelist / blacklist)
  - rotation user-agent & délais humains

- 🧠 **Analyse IA (Gemini)**
  - résumé expert
  - détection des risques mécaniques
  - détection des modifications
  - indices d’arnaque
  - scoring explicable par pilier

- 📐 **Moteur de prix (Price Engine)**
  - estimation de la cote marché via RandomForest
  - score “Deal” basé sur ratios configurables
  - recalcul automatique des scores

- 📊 **Interface Streamlit multi-pages**
  - dashboard global
  - analyse détaillée par recherche
  - navigation fluide entre recherches et annonces

- ⚙️ **Architecture robuste**
  - configuration centralisée (`AppConfig`)
  - logs structurés (console + fichier)
  - cache Streamlit maîtrisé
  - scoring 100% paramétrable

---

## 🧱 Architecture (simplifiée)

LBC_HUNTER/
├── core/ # logique métier (IA, scoring, DB, scraping)
├── frontend/ # helpers UI Streamlit
├── pages/ # pages Streamlit (multi-pages)
├── tools/ # scripts de vérification & utilitaires
├── logs/ # runtime (ignoré par git)
├── searches/ # configs de recherches (ignoré par git)
├── dashboard.py # Home Streamlit
└── main.py # Worker (scraping + IA + scoring)

---

## 🚀 Lancement

### 1️⃣ Pré-requis
- Python 3.11+
- PostgreSQL
- Une clé API Gemini

### 2️⃣ Installation
```bash
pip install -r requirements.txt