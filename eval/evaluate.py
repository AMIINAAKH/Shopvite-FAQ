"""
eval/evaluate.py — Évaluation quantitative du pipeline RAG ShopVite.

Métriques calculées (sans RAGAS pour éviter les dépendances lourdes) :
    - answer_found     : L'assistant a-t-il fourni une réponse (non hors-scope) ?
    - source_cited     : La source est-elle citée dans la réponse ?
    - confidence_score : Score numérique du niveau de confiance (high=1, medium=0.5, low=0)
    - retrieval_hit    : Au moins un chunk pertinent récupéré ?

Jeu de test : 10 questions (8 in-scope + 2 out-of-scope)
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.retrieval.vectorstore import retrieve
from src.generation.generator import Generator, determine_confidence

# ── Jeu de test ────────────────────────────────────────────────────────────────
TEST_QUESTIONS = [
    # Questions in-scope (réponses attendues dans le corpus)
    {
        "id": 1,
        "question": "Quelle est la politique de retour de ShopVite ?",
        "expected_sources": ["politique_retours.md"],
        "scope": "in",
        "expected_keywords": ["30 jours", "retour"],
    },
    {
        "id": 2,
        "question": "Combien de temps prend la livraison express ?",
        "expected_sources": ["guide_livraison.md"],
        "scope": "in",
        "expected_keywords": ["24h", "48h", "express"],
    },
    {
        "id": 3,
        "question": "Quels moyens de paiement sont acceptés ?",
        "expected_sources": ["cgv_paiement.md"],
        "scope": "in",
        "expected_keywords": ["carte", "PayPal"],
    },
    {
        "id": 4,
        "question": "Quelle est la durée de la garantie légale ?",
        "expected_sources": ["garantie_sav.md"],
        "scope": "in",
        "expected_keywords": ["2 ans", "garantie"],
    },
    {
        "id": 5,
        "question": "Quelles sont les caractéristiques du TechPhone Pro 15 ?",
        "expected_sources": ["catalogue_produits.json"],
        "scope": "in",
        "expected_keywords": ["OLED", "108MP", "5000 mAh"],
    },
    {
        "id": 6,
        "question": "La livraison est-elle gratuite ?",
        "expected_sources": ["guide_livraison.md"],
        "scope": "in",
        "expected_keywords": ["50 €", "gratuit", "offerte"],
    },
    {
        "id": 7,
        "question": "Puis-je retourner des écouteurs intra-auriculaires ?",
        "expected_sources": ["politique_retours.md"],
        "scope": "in",
        "expected_keywords": ["hygiène", "non retournable"],
    },
    {
        "id": 8,
        "question": "Comment fonctionne le programme de fidélité ?",
        "expected_sources": ["cgv_paiement.md"],
        "scope": "in",
        "expected_keywords": ["points", "Rewards", "Silver"],
    },
    # Questions out-of-scope (hors base de connaissances)
    {
        "id": 9,
        "question": "Quelle est la capitale de l'Australie ?",
        "expected_sources": [],
        "scope": "out",
        "expected_keywords": [],
    },
    {
        "id": 10,
        "question": "Pouvez-vous me recommander un restaurant à Paris ?",
        "expected_sources": [],
        "scope": "out",
        "expected_keywords": [],
    },
]

CONFIDENCE_SCORES = {"high": 1.0, "medium": 0.5, "low": 0.0}


def run_evaluation() -> dict:
    """Lance l'évaluation sur les 10 questions de test."""
    generator = Generator()
    results = []

    print("\n" + "═" * 60)
    print("  ÉVALUATION DU PIPELINE RAG — ShopVite FAQ Assistant")
    print("═" * 60 + "\n")

    for test in TEST_QUESTIONS:
        q = test["question"]
        print(f"[Q{test['id']}] {q}")

        t_start = time.time()
        chunks = retrieve(q)
        result = generator.generate(question=q, context_chunks=chunks)
        latency = round(time.time() - t_start, 2)

        answer = result["answer"]
        sources = result["sources"]
        confidence = result["confidence"]

        # ── Métriques ───────────────────────────────────────────────────────────
        answer_found = "support@shopvite.fr" not in answer and len(answer) > 50

        source_cited = any(
            s in answer for s in test["expected_sources"]
        ) if test["expected_sources"] else True  # hors-scope → pas de source attendue

        retrieval_hit = any(
            exp_src in sources for exp_src in test["expected_sources"]
        ) if test["expected_sources"] else (confidence == "low")

        keyword_hit = (
            sum(1 for kw in test["expected_keywords"] if kw.lower() in answer.lower())
            / max(len(test["expected_keywords"]), 1)
        )

        # Pour les questions hors-scope, on vérifie que l'assistant refuse correctement
        if test["scope"] == "out":
            answer_found = "support@shopvite.fr" in answer or confidence == "low"
            source_cited = True
            keyword_hit = 1.0 if answer_found else 0.0

        metrics = {
            "id": test["id"],
            "question": q,
            "scope": test["scope"],
            "answer_preview": answer[:150] + "..." if len(answer) > 150 else answer,
            "sources_returned": sources,
            "confidence": confidence,
            "confidence_score": CONFIDENCE_SCORES[confidence],
            "latency_s": latency,
            "answer_found": answer_found,
            "source_cited": source_cited,
            "retrieval_hit": retrieval_hit,
            "keyword_hit_rate": round(keyword_hit, 2),
        }

        results.append(metrics)

        status = "✓" if answer_found and retrieval_hit else "✗"
        print(f"  {status} Confidence: {confidence} | Sources: {sources} | {latency}s")
        print()

    # ── Résumé global ──────────────────────────────────────────────────────────
    n = len(results)
    summary = {
        "total_questions": n,
        "answer_found_rate": round(sum(r["answer_found"] for r in results) / n, 2),
        "retrieval_hit_rate": round(sum(r["retrieval_hit"] for r in results) / n, 2),
        "source_cited_rate": round(sum(r["source_cited"] for r in results) / n, 2),
        "avg_keyword_hit_rate": round(sum(r["keyword_hit_rate"] for r in results) / n, 2),
        "avg_confidence_score": round(sum(r["confidence_score"] for r in results) / n, 2),
        "avg_latency_s": round(sum(r["latency_s"] for r in results) / n, 2),
    }

    print("═" * 60)
    print("  RÉSUMÉ")
    print("═" * 60)
    for k, v in summary.items():
        print(f"  {k:<28} : {v}")

    # Sauvegarde des résultats
    output = {"summary": summary, "details": results}
    os.makedirs("eval", exist_ok=True)
    with open("eval/results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("\n✓ Résultats sauvegardés dans eval/results.json")

    return output


if __name__ == "__main__":
    run_evaluation()
