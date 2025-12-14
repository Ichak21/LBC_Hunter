import os
import json
import logging
from typing import Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv
from .scoring_config import SCORING_CONFIG

logger = logging.getLogger(__name__)

DEFAULT_GENERATION_CONFIG = {
    "temperature": 0.0,
    "top_p": 0.95,
    "max_output_tokens": 8192,
    "response_mime_type": "application/json",
}


class AIConfigError(RuntimeError):
    """Erreur de configuration IA (ex: clé manquante)."""


class AIResponseError(RuntimeError):
    """Erreur de réponse IA (JSON invalide / structure inattendue)."""


class AIAnalyst:
    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        generation_config: Optional[dict[str, Any]] = None,
        env_file: bool = True,
    ):
        # Chargement .env optionnel (pratique en dev, neutre en prod si env vars déjà set)
        if env_file:
            load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise AIConfigError(
                "Clé GEMINI_API_KEY introuvable. Configure-la via variables d’environnement (.env en dev)."
            )

        genai.configure(api_key=api_key)

        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config or DEFAULT_GENERATION_CONFIG,
            system_instruction=(
                "Tu es un expert automobile senior. "
                "Tu analyses des annonces pour en extraire la valeur réelle et les risques. "
                "Utilise les données déclarées (champs JSON) ET le texte pour te faire un avis."
            ),
        )

    def analyze_ad(self, ad_data: dict) -> Optional[dict]:
        """
        Retourne un dict {ai_analysis, scores} ou None si erreur non récupérable.
        """
        description = ad_data.get("description") or ad_data.get("raw_attributes", {}).get(
            "description_text", "Pas de description"
        )

        prompt = f"""
ANALYSE CETTE ANNONCE :

--- INFOS GÉNÉRALES ---
Véhicule : {ad_data.get('title')}
Prix : {ad_data.get('price')} €
Année : {ad_data.get('year')} | Km : {ad_data.get('km')}

--- INFOS VENDEUR & TECHNIQUE (Déclarées) ---
Finition déclarée : {ad_data.get('finition', 'N/A')}
Boîte : {ad_data.get('gearbox', 'N/A')}
Note Vendeur : {ad_data.get('seller_rating', 'N/A')} (sur 1.0) - {ad_data.get('seller_rating_count', 0)} avis

--- DESCRIPTION TEXTUELLE ---
\"{description}\"

--- TA MISSION ---
- IMPORTANT : Les champs "severity" doivent être compris entre 0.0 et 1.0, et refléter la gravité réelle.

- IMPORTANT: Pour "risques_meca[].severity" (0.0 à 1.0), utilise cette grille:
  * 0.05-0.15: mineur / entretien courant (petite fuite, pneus à prévoir, consommable)
  * 0.20-0.40: défaut notable mais généralement gérable (freins, suspension fatiguée, capteur, petite fuite)
  * 0.50-0.70: risque important / réparation coûteuse possible (embrayage, distribution incertaine, turbo, injecteurs)
  * 0.80-1.00: critique / danger sécurité ou panne probable (moteur HS, boîte HS, surchauffe, défaut freinage majeur)

- IMPORTANT: Pour "modifications[].severity" (0.0 à 1.0), utilise cette grille:
  * 0.05-0.15: esthétique/réversible (jantes, sono, teinte ...)
  * 0.20-0.40: modif légère (admission/échappement discret, ressorts ...)
  * 0.50-0.70: performance (stage 1, downpipe, reprog, filtre sport ...)
  * 0.80-1.00: modif lourde / risque légal/fiabilité (stage 2+, swap, suppression systèmes ...)

- IMPORTANT: Pour "indices_arnaque[].severity" (0.0 à 1.0), utilise cette grille:
  * 0.05-0.15: petit doute / incohérence légère (description très vague, manque d’infos, prix un peu bas sans preuve)
  * 0.20-0.40: suspect (prix anormalement bas, vendeur évasif, incohérences, urgence/bizarreries)
  * 0.50-0.70: très suspect (paiement inhabituel, demande d’acompte, histoire incohérente, documents flous)
  * 0.80-1.00: quasi certain / pattern classique d’arnaque (mandat cash, escrow louche, hors plateforme, “je suis à l’étranger”, usurpation)

RÉPONDS UNIQUEMENT EN JSON STRICT :
{{
  "ai_analysis": {{
    "summary": "Résumé expert en 1 phrase",
    "frais_chiffrables": [{{ "item": "ex: Pneus", "cout": 200, "raison": "Usure signalée" }}],
    "risques_meca": [{{ "nom": "ex: Bruit moteur", "severity": 0.0 }}],
    "modifications": [{{ "nom": "ex: Stage 1", "severity": 0.0 }}],
    "indices_arnaque": [{{ "nom": "ex: Mandat Cash", "severity": 0.0 }}],
    "confiance": {{
      "points_positifs": ["liste EXACTE parmi: premiere_main, carnet_entretien, factures, suivi_garage, vendeur_pro, garantie, ct_ok"],
      "points_negatifs": ["liste EXACTE parmi: orthographe_deplorable, ton_agressif, description_vague, cause_depart_suspecte"]
    }},
    "produit_evaluation": {{
      "finition_detectee": "Nom de la finition réelle (ex: S-Line) ou 'Standard'",
      "note_equipement_sur_10": 5,
      "options_majeures": ["Liste 3-4 options clés"]
    }}
  }}
}}
"""

        try:
            response = self.model.generate_content(prompt)
            raw = getattr(response, "text", None)
            if not raw:
                raise AIResponseError(
                    "Réponse IA vide (response.text manquant).")

            data = self._safe_json_loads(raw)
            self._validate_minimal_schema(data)

            return self._calculate_score(data, ad_data)

        except Exception as e:
            # Pas de print : logs exploitables
            logger.exception("Erreur analyse IA (ad_id=%s): %s",
                             ad_data.get("id"), e)
            return None

    @staticmethod
    def _safe_json_loads(text: str) -> dict:
        """
        Tente de parser du JSON strict. Si l’IA entoure de ```json ... ```,
        on nettoie proprement.
        """
        cleaned = text.strip()

        # Nettoyage léger si l’IA renvoie un bloc markdown
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise AIResponseError(f"JSON invalide: {e}") from e

    @staticmethod
    def _validate_minimal_schema(payload: dict) -> None:
        if not isinstance(payload, dict) or "ai_analysis" not in payload:
            raise AIResponseError(
                "Schéma invalide: clé 'ai_analysis' manquante.")
        if not isinstance(payload["ai_analysis"], dict):
            raise AIResponseError(
                "Schéma invalide: 'ai_analysis' n’est pas un objet.")

    def _calculate_score(self, gemini_data: dict, ad_data: dict) -> dict:
        analysis = gemini_data.get("ai_analysis", {})
        conf_cfg = SCORING_CONFIG["confiance"]
        base_scores = SCORING_CONFIG["base_scores"]

        def safe_float(val):
            try:
                return float(val) if val is not None else 0.0
            except Exception:
                return 0.0

        def safe_int(val):
            try:
                return int(val) if val is not None else 0
            except Exception:
                return 0

        def clamp01(x: float) -> float:
            return max(0.0, min(1.0, x))

        def clamp(x: float, lo: float, hi: float) -> float:
            return max(lo, min(hi, x))

        def aggregate_k(items: list[dict], cfg: dict) -> float:
            alpha = float(cfg.get("alpha", 0.7))
            sum_cap = float(cfg.get("sum_cap", 0.6))
            hard_threshold = cfg.get("hard_threshold", None)
            k_min_soft = float(cfg.get("k_min", 0.7))
            k_min_hard = float(cfg.get("k_min_hard", k_min_soft))

            sevs = [clamp01(safe_float(i.get("severity")))
                    for i in (items or [])]
            if not sevs:
                return 1.0

            s_max = max(sevs)
            s_sum = min(sum(sevs), sum_cap)

            penalty = (alpha * s_max) + ((1.0 - alpha) * s_sum)
            k = 1.0 - penalty
            k_min = k_min_soft
            if hard_threshold is not None and s_max >= float(hard_threshold):
                k_min = k_min_hard

            return clamp(k, k_min, 1.0)
            return clamp(k, k_min, 1.0)
        # --- B. CALCUL FIABILITÉ (K) ---
        sev_cfg = SCORING_CONFIG.get("severity", {})

        k_meca = aggregate_k(analysis.get(
            "risques_meca", []), sev_cfg.get("meca", {}))
        k_modif = aggregate_k(analysis.get(
            "modifications", []), sev_cfg.get("modif", {}))
        k_arnaque = aggregate_k(analysis.get(
            "indices_arnaque", []), sev_cfg.get("arnaque", {}))

        # --- C. PRIX VIRTUEL (S_DEAL) ---
        prix_affiche = safe_int(ad_data.get("price"))
        cout_repa = sum((item.get("cout") or 0)
                        for item in analysis.get("frais_chiffrables", []))
        prix_virtuel = prix_affiche + cout_repa
        s_deal = base_scores["deal"]

        # --- D. CONFIANCE (S_CONF) ---
        s_conf = base_scores["conf"]

        for tag in analysis.get("confiance", {}).get("points_positifs", []):
            val = conf_cfg["bonus_tags"].get(
                tag, conf_cfg["default_bonus_val"])
            s_conf += val

        for tag in analysis.get("confiance", {}).get("points_negatifs", []):
            val = conf_cfg["malus_tags"].get(
                tag, conf_cfg["default_malus_val"])
            s_conf += val

        rating = ad_data.get("seller_rating")
        count = ad_data.get("seller_rating_count", 0)

        if rating is not None and count >= conf_cfg["seller"]["min_reviews"]:
            if rating >= conf_cfg["seller"]["top_threshold"]:
                s_conf += conf_cfg["seller"]["bonus_val"]
            elif rating < conf_cfg["seller"]["bad_threshold"]:
                s_conf += conf_cfg["seller"]["malus_val"]

        desc_len = len((ad_data.get("description") or "").split())
        if desc_len < conf_cfg["description"]["short_len"]:
            s_conf += conf_cfg["description"]["short_pen"]
        elif desc_len > conf_cfg["description"]["long_len"]:
            s_conf += conf_cfg["description"]["long_bon"]

        s_conf = max(0, min(100, s_conf))

        # --- E. PRODUIT (S_PROD) ---
        note_expert = analysis.get("produit_evaluation", {}).get(
            "note_equipement_sur_10", 5)
        s_prod = safe_float(note_expert) * 10
        s_prod = max(0, min(100, s_prod))

        # --- F. SCORE FINAL ---
        weights = SCORING_CONFIG["weights"]
        score_base = (s_deal * weights["deal"]) + (s_conf *
                                                   weights["conf"]) + (s_prod * weights["prod"])

        indice_fiabilite = k_meca * k_modif * k_arnaque
        score_final = score_base * indice_fiabilite

        return {
            "ai_analysis": analysis,
            "scores": {
                "total": round(score_final, 1),
                "base": {"deal": s_deal, "conf": s_conf, "prod": s_prod},
                "sanity_checks": {
                    "k_meca": round(k_meca, 2),
                    "k_modif": round(k_modif, 2),
                    "k_arnaque": round(k_arnaque, 2),
                },
                "financial": {
                    "posted_price": int(prix_affiche),
                    "repair_cost": int(cout_repa),
                    "virtual_price": int(prix_virtuel),
                },
            },
        }
