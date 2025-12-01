# -*- coding: utf-8 -*-
"""
llm_repro_eval.py
-----------------
Komplettes Reproduzierbarkeits-Evaluationsscript:

1) URL wird per CLI übergeben.
2) HTML wird geladen.
3) Dasselbe HTML wird 10x durch run_llm_analysis geschickt.
4) Pro Indikator wird BERTScore gegen Run 1 berechnet.
5) Zusätzlich globaler BERTScore (Mittel über Indikatoren).
6) Es wird NUR EINE Ergebnisdatei gespeichert, benannt nach der URL.

Speicherort:
    /home/till/sustainability_checker/app/evaluation/results/LLM_repro/
"""

import asyncio
import sys
import os
import json
import re
import statistics
from urllib.parse import urlparse

import aiohttp

# BERTScore
# pip install bert-score torch transformers
from bert_score import score as bertscore

from app.modules.manager.page_info_extractor import run_llm_analysis
from app.core.config import settings


# ============================================================
# 🔧 Speicherpfad
# ============================================================

BASE_DIR = "/home/till/sustainability_checker/app/evaluation/results/LLM_repro"
os.makedirs(BASE_DIR, exist_ok=True)


# ============================================================
# 📥 HTML laden
# ============================================================

async def download_html(url: str) -> str:
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as r:
            r.raise_for_status()
            return await r.text()


# ============================================================
# 🧹 Normalisierung: Listen joinen, None → ""
# ============================================================

def normalize_value(v):
    """
    - list -> "; ".join(...)
    - dict -> JSON string
    - None -> ""
    - str -> stripped str
    """
    if v is None:
        return ""
    if isinstance(v, list):
        return "; ".join(str(x).strip() for x in v if str(x).strip())
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return str(v).strip()


def normalize_output(d: dict) -> dict:
    if not isinstance(d, dict):
        return {}
    return {k: normalize_value(v) for k, v in d.items()}


# ============================================================
# 🏷️ Dateiname aus URL bauen
# ============================================================

def safe_filename_from_url(url: str) -> str:
    p = urlparse(url)
    base = (p.netloc + p.path).strip("/")
    if not base:
        base = p.netloc or "result"
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", base)
    return base[:120]  # nicht endlos lang


# ============================================================
# 🔍 BERTScore pro Feld + global
# ============================================================

def compute_bertscore(reference: dict, candidate: dict, lang: str = "de"):
    """
    Berechnet BERTScore je Feld (gegen Referenz).
    Rückgabe:
      field_scores: {field: {"P":..,"R":..,"F1":..}}
      global_score: {"P":..,"R":..,"F1":..}
    """
    ref_norm = normalize_output(reference)
    cand_norm = normalize_output(candidate)

    fields = sorted(set(ref_norm.keys()) | set(cand_norm.keys()))

    # Texte je Feld paarweise vorbereiten
    refs = [ref_norm.get(f, "") for f in fields]
    cands = [cand_norm.get(f, "") for f in fields]

    # BERTScore (one-to-one, daher gleiche Listenlänge)
    P, R, F1 = bertscore(
        cands,
        refs,
        lang=lang,
        rescale_with_baseline=True
    )

    field_scores = {}
    for i, f in enumerate(fields):
        field_scores[f] = {
            "P": float(P[i]),
            "R": float(R[i]),
            "F1": float(F1[i]),
            "ref_text": refs[i],
            "cand_text": cands[i]
        }

    global_score = {
        "P": float(P.mean()),
        "R": float(R.mean()),
        "F1": float(F1.mean())
    }

    return field_scores, global_score


def aggregate_field_scores(all_field_scores):
    """
    all_field_scores: Liste von field_scores (pro Run)
    -> Mittelwert / Std je Feld
    """
    if not all_field_scores:
        return {}

    fields = all_field_scores[0].keys()
    agg = {}

    for f in fields:
        f1s = [fs[f]["F1"] for fs in all_field_scores if f in fs]
        ps  = [fs[f]["P"]  for fs in all_field_scores if f in fs]
        rs  = [fs[f]["R"]  for fs in all_field_scores if f in fs]

        agg[f] = {
            "mean_F1": statistics.mean(f1s) if f1s else None,
            "std_F1": statistics.pstdev(f1s) if len(f1s) > 1 else 0.0,
            "mean_P":  statistics.mean(ps) if ps else None,
            "std_P":  statistics.pstdev(ps) if len(ps) > 1 else 0.0,
            "mean_R":  statistics.mean(rs) if rs else None,
            "std_R":  statistics.pstdev(rs) if len(rs) > 1 else 0.0,
            "unique_values": len(set(
                normalize_value(fs[f]["cand_text"]) for fs in all_field_scores if f in fs
            ))
        }

    return agg


# ============================================================
# 🔬 Hauptfunktion
# ============================================================

async def evaluate_reproducibility(url: str, runs: int = 10, lang: str = "de"):
    print(f"📥 Lade HTML von {url} …")
    html = await download_html(url)
    print(f"📄 HTML-Länge: {len(html)} Zeichen")

    print(f"\n⚙️ Starte {runs} LLM-Analysen …")

    results = []
    for i in range(1, runs + 1):
        print(f"\n🧠 LLM RUN {i}/{runs}")
        out = await run_llm_analysis(html, url, settings.OPENAI_API_KEY)
        results.append(out)
        print(f"   ✔ Keys: {list(out.keys())}")

    # Referenz = Run 1
    reference = results[0]

    print("\n📊 BERTScore gegen Referenz (Run 1) …")

    per_run_field_scores = []
    per_run_global_scores = []

    for i, cand in enumerate(results[1:], start=2):
        field_scores, global_score = compute_bertscore(reference, cand, lang=lang)

        per_run_field_scores.append(field_scores)
        per_run_global_scores.append(global_score)

        print(f"   RUN 1 ↔ RUN {i}: global F1={global_score['F1']:.4f}")

    # Aggregation
    field_agg = aggregate_field_scores(per_run_field_scores)

    global_F1s = [g["F1"] for g in per_run_global_scores]
    global_agg = {
        "mean_F1": statistics.mean(global_F1s) if global_F1s else None,
        "std_F1": statistics.pstdev(global_F1s) if len(global_F1s) > 1 else 0.0,
        "min_F1": min(global_F1s) if global_F1s else None,
        "max_F1": max(global_F1s) if global_F1s else None,
    }

    # Enddatei speichern
    fname = safe_filename_from_url(url) + ".json"
    out_path = os.path.join(BASE_DIR, fname)

    final_obj = {
        "url": url,
        "runs": runs,
        "reference_run_index": 1,
        "llm_outputs": results,  # alle Runs drin, aber nur hier
        "bertscore": {
            "per_run_vs_reference": [
                {
                    "run_index": i + 1,
                    "field_scores": per_run_field_scores[i - 1],
                    "global_score": per_run_global_scores[i - 1]
                }
                for i in range(1, runs)  # Runs 2..N
            ],
            "field_aggregate": field_agg,
            "global_aggregate": global_agg
        }
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final_obj, f, indent=2, ensure_ascii=False)

    print(f"\n📁 Fertig. Ergebnis gespeichert in:\n   {out_path}\n")


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Verwendung:")
        print('  PYTHONPATH=. python3 app/evaluation/llm_repro_eval.py "https://example.org/"')
        sys.exit(1)

    url = sys.argv[1]
    asyncio.run(evaluate_reproducibility(url))
