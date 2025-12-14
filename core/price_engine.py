import logging
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from .db_client import DatabaseClient
from .models import Ad
from .scoring_config import SCORING_CONFIG
from .search_manager import SearchManager

logger = logging.getLogger(__name__)


class PriceEngine:
    def __init__(self, db_client: DatabaseClient):
        self.db = db_client

        params = SCORING_CONFIG["price_engine"]["model_params"]
        self.model = RandomForestRegressor(
            n_estimators=int(params["n_estimators"]),
            random_state=int(params["random_state"]),
        )
        self.is_trained = False

        # MÉMOIRE DU MODÈLE
        self.model_meta: Dict[str, Any] = {
            "features_used": [],
            "imputers": {},
        }

    def get_data_for_search(self, search_id: str) -> pd.DataFrame:
        try:
            rows = self.db.fetch_ads_for_price_training(search_id)
            if not rows:
                return pd.DataFrame()

            df = pd.DataFrame(rows)
            if df.empty:
                return pd.DataFrame()

            df = df.dropna(subset=["price", "year", "mileage"])

            veto = SCORING_CONFIG["price_engine"].get("veto", {})
            min_k = float(veto.get("min_k_arnaque_for_market", 0.5))
            exclude_user = set(veto.get("exclude_user_status", []))
            exclude_status = set(veto.get("exclude_status", []))
            require_scores = bool(veto.get("require_ai_scores", True))

            if require_scores:
                df = df[df["has_scores"] == True]
                df = df[df["k_arnaque"].notna()]

            df = df[df["k_arnaque"] >= min_k]

            if exclude_user:
                df = df[~df["user_status"].isin(exclude_user)]
            if exclude_status:
                df = df[~df["status"].isin(exclude_status)]

            if df.empty:
                return pd.DataFrame()

            # prix aberrant relatif (ratio * médiane/mean)
            price_floor_ratio = float(veto.get("price_floor_ratio", 0.30))
            price_floor_stat = str(
                veto.get("price_floor_stat", "median")).lower()
            legacy_min_price = veto.get("min_price_aberrant", None)

            stat_val = float(df["price"].mean()) if price_floor_stat == "mean" else float(
                df["price"].median())
            if stat_val > 0:
                df = df[df["price"] >= price_floor_ratio * stat_val]
            elif legacy_min_price is not None:
                df = df[df["price"] >= int(legacy_min_price)]

            if df.empty:
                return pd.DataFrame()

            # outliers
            limits = SCORING_CONFIG["price_engine"]["outliers"]
            df = df[
                (df["price"] >= limits["min_price"]) &
                (df["price"] <= limits["max_price"]) &
                (df["mileage"] >= limits["min_mileage"]) &
                (df["mileage"] <= limits["max_mileage"])
            ]

            if df.empty:
                return pd.DataFrame()

            return df[["price", "year", "mileage", "horsepower"]].copy()

        except Exception as e:
            logger.exception(
                "Erreur get_data_for_search(%s): %s", search_id, e)
            return pd.DataFrame()

    def train(self, search_id: str, df: pd.DataFrame) -> None:
        training_cfg = SCORING_CONFIG["price_engine"].get("training", {})
        min_samples = int(training_cfg.get("min_samples", 30))

        if df is None or df.empty or len(df) < min_samples:
            logger.warning(
                "Pas assez de données propres pour entraîner (n=%s < min_samples=%s) [search=%s]",
                0 if df is None else len(df),
                min_samples,
                search_id,
            )
            self.is_trained = False
            SearchManager.update_model_meta(search_id, {"r2_score": "N/A"})
            return

        # 1) FEATURES OBLIGATOIRES
        base_features = ["year", "mileage"]
        final_features = base_features.copy()

        # 2) FEATURES DYNAMIQUES
        dyn_conf = SCORING_CONFIG["price_engine"]["dynamic_features"]
        for col in dyn_conf.get("candidates", []):
            if col in df.columns:
                fill_rate = df[col].notna().mean()
                if fill_rate >= float(dyn_conf.get("min_fill_rate", 0.6)):
                    median_val = float(df[col].median())
                    self.model_meta["imputers"][col] = median_val
                    df[col] = df[col].fillna(median_val)
                    final_features.append(col)
                    logger.info(
                        "Feature retenue: %s (fill_rate=%.0f%%)", col, fill_rate * 100)
                else:
                    logger.info(
                        "Feature rejetée: %s (fill_rate=%.0f%%)", col, fill_rate * 100)

        self.model_meta["features_used"] = final_features

        # 3) ENTRAÎNEMENT
        X = df[final_features]
        y = df["price"]

        self.model.fit(X, y)
        self.is_trained = True

        # Score R² (sur train, conforme à ton implémentation)
        score = float(self.model.score(X, y))
        logger.info(
            "Modèle entraîné [search=%s] features=%s R²=%.2f", search_id, final_features, score)
        SearchManager.update_model_meta(
            search_id, {"r2_score": round(score, 2)})

    def predict_price(self, year: int, km: int, hp: int | None = None) -> Optional[float]:
        if not self.is_trained:
            return None

        try:
            input_data: Dict[str, Any] = {"year": year, "mileage": km}

            for col in self.model_meta["features_used"]:
                if col in ("year", "mileage"):
                    continue

                if col == "horsepower":
                    input_data[col] = hp if hp is not None else self.model_meta["imputers"].get(
                        col, 0)

            features_df = pd.DataFrame([input_data])[
                self.model_meta["features_used"]]
            predicted = float(self.model.predict(features_df)[0])
            return round(predicted, 2)

        except Exception as e:
            logger.exception("Erreur predict_price: %s", e)
            return None

    @staticmethod
    def _deal_score_from_ratio(ratio: float) -> float:
        cfg = SCORING_CONFIG["price_engine"]["scoring"]

        r_good = float(cfg["good_deal_ratio"])
        r_neutral = float(cfg.get("neutral_ratio", 1.0))
        r_bad = float(cfg["bad_deal_ratio"])

        if ratio <= r_good:
            return 100.0
        if ratio >= r_bad:
            return 0.0

        if ratio <= r_neutral:
            # 100 → 50
            return 50.0 + (r_neutral - ratio) * (50.0 / (r_neutral - r_good))
        else:
            # 50 → 0
            return 50.0 - (ratio - r_neutral) * (50.0 / (r_bad - r_neutral))

    def update_deal_scores(self, search_id: str) -> None:
        logger.info("Audit du marché [search=%s]...", search_id)

        df = self.get_data_for_search(search_id)
        if df.empty:
            logger.warning(
                "Dataset marché vide après veto/outliers [search=%s].", search_id)
            self.is_trained = False
            SearchManager.update_model_meta(search_id, {"r2_score": "N/A"})
            return

        self.train(search_id, df)
        if not self.is_trained:
            logger.warning(
                "Modèle non entraîné, deal scores non mis à jour [search=%s].", search_id)
            return

        try:
            ads = self.db.fetch_active_ads_for_deal_update(search_id)
            updates = []

            for ad in ads:
                year = ad.get("year")
                mileage = ad.get("mileage")
                if not year or not mileage:
                    continue

                fair_price = self.predict_price(
                    year, mileage, ad.get("horsepower"))
                if not fair_price or fair_price <= 0:
                    continue

                # prix virtuel
                repair_cost = 0
                ai_analysis = ad.get("ai_analysis") or {}
                for frais in ai_analysis.get("frais_chiffrables", []):
                    repair_cost += int(frais.get("cout") or 0)

                price = int(ad.get("price") or 0)
                virtual_price = price + repair_cost

                ratio = virtual_price / fair_price if fair_price > 0 else 1.0

                s_deal = self._deal_score_from_ratio(ratio)
                s_deal = max(0.0, min(100.0, s_deal))

                current_scores = dict(ad.get("scores") or {})
                current_scores.setdefault("base", {})
                current_scores.setdefault("financial", {})

                current_scores["base"]["deal"] = int(round(s_deal))
                current_scores["financial"]["market_estimation"] = int(
                    round(fair_price))
                current_scores["financial"]["virtual_price"] = int(
                    virtual_price)

                # Recalcul total
                s_conf = float(current_scores.get("base", {}).get("conf", 50))
                s_prod = float(current_scores.get("base", {}).get("prod", 0))
                weights = SCORING_CONFIG["weights"]

                total = (s_deal * weights["deal"]) + (s_conf *
                                                      weights["conf"]) + (s_prod * weights["prod"])

                sanity = current_scores.get("sanity_checks", {})
                k_meca = float(sanity.get("k_meca", 1.0))
                k_modif = float(sanity.get("k_modif", 1.0))
                k_arnaque = float(sanity.get("k_arnaque", 1.0))

                current_scores["total"] = round(
                    total * k_meca * k_modif * k_arnaque, 1)

                updates.append({"id": ad["id"], "scores": current_scores})

            updated = self.db.bulk_update_scores(updates)
            logger.info(
                "Market Update OK: %s cotes mises à jour [search=%s].", updated, search_id)

        except Exception as e:
            logger.exception("Erreur update_deal_scores(%s): %s", search_id, e)
