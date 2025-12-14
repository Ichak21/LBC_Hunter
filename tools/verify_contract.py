from _bootstrap import PROJECT_ROOT  # noqa: F401

from core.scoring_config import SCORING_CONFIG
from core.app_config import load_app_config


def fail(msg: str):
    print(f"❌ CONTRACT FAIL: {msg}")
    sys.exit(1)


def ok(msg: str):
    print(f"✅ {msg}")


def check_weights():
    weights = SCORING_CONFIG.get("weights")
    if not weights:
        fail("weights manquants")

    total = sum(weights.values())
    if abs(total - 1.0) > 1e-6:
        fail(f"weights somme != 1.0 ({total})")

    for k, v in weights.items():
        if v < 0:
            fail(f"weight négatif: {k}")

    ok("weights OK")


def check_price_engine():
    pe = SCORING_CONFIG.get("price_engine", {})
    scoring = pe.get("scoring", {})

    r_good = scoring.get("good_deal_ratio")
    r_neutral = scoring.get("neutral_ratio")
    r_bad = scoring.get("bad_deal_ratio")

    if not (r_good and r_neutral and r_bad):
        fail("ratios price_engine incomplets")

    if not (r_good < r_neutral < r_bad):
        fail("ordre ratios invalide (good < neutral < bad)")

    ok("price_engine ratios OK")


def check_severity():
    sev = SCORING_CONFIG.get("severity", {})
    modif = sev.get("modif", {})

    k_min = modif.get("k_min")
    k_min_hard = modif.get("k_min_hard")
    hard_threshold = modif.get("hard_threshold")

    if hard_threshold is not None:
        if not (0.0 < hard_threshold <= 1.0):
            fail("hard_threshold hors bornes")

        if k_min_hard > k_min:
            fail("k_min_hard > k_min (incohérent)")

    ok("severity modif OK")


def check_app_config():
    cfg = load_app_config()

    if cfg.streamlit.cache_ttl_seconds <= 0:
        fail("STREAMLIT_CACHE_TTL invalide")

    if cfg.worker.gemini_sleep_seconds <= 0:
        fail("WORKER_GEMINI_SLEEP invalide")

    if cfg.worker.archive_days_threshold < 0:
        fail("WORKER_ARCHIVE_DAYS invalide")

    ok("AppConfig runtime OK")


def main():
    print("🔍 Vérification contrat white paper...\n")

    check_weights()
    check_price_engine()
    check_severity()
    check_app_config()

    print("\n🎉 CONTRAT OK — aligné white paper")


if __name__ == "__main__":
    main()
