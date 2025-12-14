# scoring_config.py

# C'est ici que tu règles la sensibilité du bot sans toucher au code.
SCORING_CONFIG = {
    # --- A. FORMULE MAÎTRESSE (Pondération des piliers) ---
    # Total doit faire 1.0 (ou 100%)
    "weights": {
        "deal": 0.5,   # 50% Prix/Frais (Calculé par le PriceEngine)
        "conf": 0.3,   # 30% Confiance (Calculé par l'IA + Stats Vendeur)
        "prod": 0.2    # 20% Produit (Note IA sur les options/finition)
    },

    # --- B. VALEURS DE BASE ---
    "base_scores": {
        "deal": 50,  # Valeur par défaut avant calcul mathématique
        "conf": 50,  # Valeur neutre
        "prod": 0    # Le produit est noté de 0 à 10 par l'IA, donc part de 0
    },

    # --- C. PILIER CONFIANCE (Règles) ---
    "confiance": {
        "default_bonus_val": 5,
        "default_malus_val": -5,

        # Mots-clés détectés par Gemini (Bonus)
        "bonus_tags": {
            "premiere_main": 15,
            "carnet_entretien": 10,
            "factures": 10,
            "suivi_garage": 5,
            "vendeur_pro": 5,
            "garantie": 5,
            "ct_ok": 5
        },
        # Mots-clés détectés par Gemini (Malus)
        "malus_tags": {
            "orthographe_deplorable": -15,
            "ton_agressif": -10,
            "description_vague": -10,
            "cause_depart_suspecte": -5
        },
        # Note Vendeur Leboncoin (0.0 à 1.0)
        "seller": {
            "min_reviews": 5,       # Minimum d'avis pour être pris en compte
            "top_threshold": 0.90,  # > 90% satisfaits -> Bonus
            "bad_threshold": 0.60,  # < 60% satisfaits -> Malus
            "bonus_val": 10,
            "malus_val": -10
        },
        # Longueur de la description (indicateur d'effort)
        "description": {
            "short_len": 10,   # < 10 mots
            "short_pen": -15,  # Grosse pénalité
            "long_len": 100,   # > 100 mots
            "long_bon": 5      # Petit bonus
        }
    },

    # --- D. MOTEUR DE PRIX (Price Engine) ---
    "price_engine": {
        # Paramètres de l'IA Mathématique (Random Forest)
        "model_params": {
            "n_estimators": 100,  # Nombre d'arbres de décision
            "random_state": 42   # Pour avoir des résultats reproductibles
        },

        # Seuils pour nettoyer les données aberrantes (Outliers) avant d'apprendre
        "outliers": {
            "min_price": 500,       # On ignore les épaves symboliques
            "max_price": 200000,    # On ignore les erreurs de saisie millions
            "min_mileage": 500,     # On ignore les fausses voitures neuves
            "max_mileage": 900000   # On ignore les erreurs de km
        },

        # Gestion Dynamique des Colonnes (Smart Feature Selection)
        "dynamic_features": {
            # Seuil : Si une colonne est remplie à moins de X%, on la jette.
            "min_fill_rate": 0.6,  # 30% des annonces doivent avoir l'info

            # Liste des colonnes qu'on tente d'utiliser si elles sont remplies
            # (On ne met pas 'finition' pour l'instant car c'est du texte sale)
            "candidates": ["horsepower"]
        },

        # Paramètres de calcul du Score Deal
        "scoring": {
            # Si (Prix+Repa) / Cote < 0.8 -> Top affaire
            "good_deal_ratio": 0.5,   # => 100
            "neutral_ratio": 1.0,     # => 50
            "bad_deal_ratio": 1.5     # => 0
        },
        "training": {
            # (choix v1) >10 pour éviter l'instabilité, <50 pour ne pas bloquer trop souvent
            "min_samples": 15,
        },
        "veto": {
            "min_k_arnaque_for_market": 0.5,
            "price_floor_ratio": 0.30,     # < 30% médiane => aberrant
            "price_floor_stat": "median",  # median ou mean
            "exclude_user_status": ["TRASH", "SCAM_MANUAL"],
            "exclude_status": ["SCAM"],
            "require_ai_scores": True
        },
    },
    # --- E. K modif coef ---
    "severity": {
        # Agrégation saturée = (alpha * max) + (1-alpha) * min(sum, sum_cap)
        # puis K = 1 - penalty, borné par k_min.

        "meca": {
            "alpha": 0.40,   # plus cumulatif (le max compte, mais pas trop)
            # on laisse cumuler davantage (plusieurs risques mécas peuvent s'additionner)
            "sum_cap": 1.00,
            "k_min": 0.25,   # si c'est vraiment mauvais, ça peut descendre bas
        },
        "modif": {
            "alpha": 0.75,
            "sum_cap": 0.60,

            # Planchers à 2 étages
            "k_min": 0.70,            # plancher “soft”
            "hard_threshold": 0.80,   # si max severity >= 0.80 → modif lourde
            "k_min_hard": 0.30,       # plancher “hard” (stage2+, swap, etc.)
        },
        "arnaque": {
            "alpha": 0.90,   # quasi worst-case
            "sum_cap": 0.40,  # quelques signaux s'additionnent mais cap vite
            "k_min": 0.05,   # un gros signal peut quasiment tuer le score
        },
    }
}
