from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple


@dataclass(frozen=True)
class KParams:
    alpha: float
    sum_cap: float
    k_min: float


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def clamp01(x: float) -> float:
    return clamp(x, 0.0, 1.0)


def aggregate_k(severities: Iterable[float], p: KParams) -> float:
    sevs = [clamp01(float(s)) for s in severities]
    if not sevs:
        return 1.0

    s_max = max(sevs)
    s_sum = min(sum(sevs), p.sum_cap)

    penalty = (p.alpha * s_max) + ((1.0 - p.alpha) * s_sum)
    k = 1.0 - penalty
    return clamp(k, p.k_min, 1.0)


def explain(severities: List[float], p: KParams) -> Tuple[float, dict]:
    sevs = [clamp01(float(s)) for s in severities]
    if not sevs:
        return 1.0, {"s_max": 0.0, "s_sum_capped": 0.0, "penalty": 0.0, "k_raw": 1.0}

    s_max = max(sevs)
    s_sum = min(sum(sevs), p.sum_cap)
    penalty = (p.alpha * s_max) + ((1.0 - p.alpha) * s_sum)
    k_raw = 1.0 - penalty
    k = clamp(k_raw, p.k_min, 1.0)

    return k, {"s_max": s_max, "s_sum_capped": s_sum, "penalty": penalty, "k_raw": k_raw}


def run_scenarios(title: str, p: KParams, scenarios: List[Tuple[str, List[float]]]) -> None:
    print(f"\n=== {title} ===")
    print(
        f"params: alpha={p.alpha:.2f}  sum_cap={p.sum_cap:.2f}  k_min={p.k_min:.2f}\n")
    for name, sevs in scenarios:
        k, d = explain(sevs, p)
        print(
            f"- {name:<28} sevs={sevs!s:<18} "
            f"=> k={k:.3f}  (max={d['s_max']:.2f}, sum_cap={d['s_sum_capped']:.2f}, pen={d['penalty']:.2f}, raw={d['k_raw']:.3f})"
        )


if __name__ == "__main__":
    # 🔧 Mets ici EXACTEMENT les paramètres que tu as dans SCORING_CONFIG["severity"]
    p_meca = KParams(alpha=0.40, sum_cap=1.00, k_min=0.25)
    p_modif = KParams(alpha=0.75, sum_cap=0.60, k_min=0.70)
    p_arnaque = KParams(alpha=0.90, sum_cap=0.40, k_min=0.05)

    # ✅ Scénarios “type” (modifie selon tes cas réels)
    scenarios_modif = [
        ("aucune modif", []),
        ("jantes + teinte (léger)", [0.10, 0.10]),
        ("3 petites modifs", [0.20, 0.20, 0.20]),
        ("echappement + ressorts", [0.30, 0.30]),
        ("stage 1 seul", [0.60]),
        ("stage1 + 2 légères", [0.60, 0.15, 0.15]),
        ("stage2+", [0.90]),
    ]

    scenarios_meca = [
        ("aucun risque", []),
        ("entretien courant", [0.10]),
        ("2 défauts moyens", [0.30, 0.30]),
        ("embrayage suspect", [0.60]),
        ("turbo + injecteurs", [0.60, 0.60]),
        ("critique sécurité", [0.90]),
    ]

    scenarios_arnaque = [
        ("aucun indice", []),
        ("vague / petit doute", [0.10]),
        ("2 signaux suspects", [0.30, 0.30]),
        ("acompte demandé", [0.60]),
        ("mandat cash (gros)", [0.90]),
        ("plusieurs gros signaux", [0.70, 0.80]),
    ]

    run_scenarios("K_MODIF", p_modif, scenarios_modif)
    run_scenarios("K_MECA", p_meca, scenarios_meca)
    run_scenarios("K_ARNAQUE", p_arnaque, scenarios_arnaque)

    # ✨ Bonus : un petit tableau “sensibilité” sur un pattern fixe
    print("\n=== Sensibilité rapide (pattern: [0.3,0.3,0.3]) ===")
    pattern = [0.3, 0.3, 0.3]
    for alpha in [0.3, 0.5, 0.7, 0.85]:
        for sum_cap in [0.4, 0.6, 0.8, 1.0]:
            k = aggregate_k(pattern, KParams(
                alpha=alpha, sum_cap=sum_cap, k_min=0.0))
            print(f"alpha={alpha:.2f} sum_cap={sum_cap:.2f} => k={k:.3f}")
