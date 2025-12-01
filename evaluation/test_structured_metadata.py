# file: app/evaluation/test_structured_metadata.py
# -*- coding: utf-8 -*-

import os
import sys
import json
import asyncio
import statistics
from urllib.parse import urlparse

import aiohttp

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.modules.analysis.structured_metadata import check_f2a_f2b_for_url


# ---------------------------------------------------------
# RUN A SINGLE FAIR-CHECKER CALL
# ---------------------------------------------------------

async def run_single(url: str, session: aiohttp.ClientSession) -> dict:
    result = await check_f2a_f2b_for_url(session, url)
    f2a = result.get("F2A", {}) or {}
    f2b = result.get("F2B", {}) or {}

    return {
        "rdf_count": f2a.get("rdf_count"),
        "uses_vocabulary": f2b.get("uses_shared_vocabularies"),
        "score_f2a": f2a.get("score"),
        "score_f2b": f2b.get("score"),
    }


# ---------------------------------------------------------
# MAIN BENCHMARK
# ---------------------------------------------------------

async def evaluate_structured_metadata(url: str, runs: int = 10):
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")

    save_path = f"app/evaluation/results/structured_metadata/{domain}.json"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    print(f"\n🌐 Starte Structured-Metadata-Analyse für: {url}")
    print(f"🧪 Durchläufe: {runs}\n")

    rdf_counts = []
    vocab_results = []
    raw_runs = []

    async with aiohttp.ClientSession() as session:
        for i in range(runs):
            print(f"▶️ Run {i+1}/{runs}")
            data = await run_single(url, session)

            rdf_counts.append(data["rdf_count"])
            vocab_results.append(data["uses_vocabulary"])
            raw_runs.append(data)

            print(f"   RDF: {data['rdf_count']}, Vocabulary: {data['uses_vocabulary']}")

            await asyncio.sleep(0.3)

    # --------------------------------------
    # FINAL STATISTICS
    # --------------------------------------

    # RDF StdDev
    valid_counts = [x for x in rdf_counts if x is not None]
    rdf_stddev = round(statistics.stdev(valid_counts), 3) if len(valid_counts) > 1 else 0.0

    # Vocabulary consistency = immer gleich?
    vocab_consistent = len(set(vocab_results)) == 1

    # --------------------------------------
    # SAVE JSON
    # --------------------------------------

    out = {
        "url": url,
        "runs": runs,

        "rdf_counts": rdf_counts,
        "vocab_results": vocab_results,
        "raw_runs": raw_runs,

        "rdf_stddev": rdf_stddev,
        "vocab_consistent": vocab_consistent,
    }

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print(f"\n📂 Ergebnisse gespeichert unter:\n   {save_path}\n")
    print("🎉 Fertig!")


# ---------------------------------------------------------
# CLI ENTRYPOINT
# ---------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Nutzung:")
        print("   python app/evaluation/test_structured_metadata.py <URL>")
        sys.exit(1)

    url = sys.argv[1]
    asyncio.run(evaluate_structured_metadata(url))
