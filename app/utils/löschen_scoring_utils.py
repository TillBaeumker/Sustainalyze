# file: app/utils/löschen_scoring_utils.py
from __future__ import annotations
from typing import Any, Dict, List, Optional

# --------- Generische Helpers ---------
def as_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []

def is_num(x: Any) -> bool:
    return isinstance(x, (int, float))

def band_for(score: Optional[int]) -> str:
    if score is None:
        return "unbekannt"
    if score >= 70:
        return "nachhaltig"
    if score >= 40:
        return "teilweise nachhaltig"
    return "nicht nachhaltig"

def is_present(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, list):
        return any(is_present(x) for x in v)
    return bool(str(v).strip())

def norm_text(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        parts = [norm_text(x) for x in v]
        parts = [p for p in parts if p]
        return ", ".join(sorted(set(parts)))
    return " ".join(str(v).strip().split()).lower()

def weighted_total(components: Dict[str, Dict[str, Any]], weights: Dict[str, float]) -> Optional[int]:
    """
    components: {key: {"score": int|None, ...}}
    weights:    {key: float}
    -> renormalisierte Gewichtung über alle vorhandenen (score!=None)
    """
    usable: List[tuple[int, float]] = []
    total_w = 0.0
    for k, payload in components.items():
        sc = payload.get("score")
        w = float(weights.get(k, 0.0))
        if sc is None or w <= 0:
            continue
        usable.append((int(sc), w))
        total_w += w

    if not usable or total_w <= 0:
        return None

    acc = 0.0
    for sc, w in usable:
        acc += sc * (w / total_w)
    return int(round(acc))





