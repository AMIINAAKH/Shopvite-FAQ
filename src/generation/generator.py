"""
generator.py — Génération de réponses RAG.

Appel Mistral via HTTP direct (compatible avec les contraintes réseau du sandbox).
La clé API est lue depuis les variables d'environnement.
"""

import os, json, urllib.request, urllib.error
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

# ── System Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es l'assistant virtuel de ShopVite, une boutique en ligne spécialisée en électronique. \
Tu réponds aux questions des clients de manière professionnelle, concise et toujours en français.

## RÈGLES ABSOLUES

1. **Réponds UNIQUEMENT à partir du contexte fourni** entre les balises <contexte> et </contexte>.
2. **Ne jamais inventer** de prix, de délais, de politiques ou de caractéristiques produits.
3. **Si la question est hors-contexte** (pas d'information dans les documents), réponds :
   "Je n'ai pas l'information nécessaire pour répondre à cette question dans ma base de connaissances. \
Je vous invite à contacter notre support : support@shopvite.fr ou au 0800 123 456."
4. **Cite toujours la source** à la fin de ta réponse entre parenthèses, ex : *(Source : guide_livraison.md)*
5. **Sois concis** : 2 à 5 phrases maximum, sauf si une liste structurée est nécessaire.
6. **Ton** : professionnel, chaleureux, sans jargon technique inutile.

## EXEMPLES

Question : "Combien de temps ai-je pour retourner un produit ?"
Réponse : "Vous disposez de **30 jours calendaires** à compter de la date de réception pour retourner \
tout produit, sans justification requise. Pour un produit défectueux, ce délai est étendu à 60 jours. \
*(Source : politique_retours.md)*"

Question : "Quelle est la météo à Paris demain ?"
Réponse : "Je n'ai pas l'information nécessaire pour répondre à cette question dans ma base de \
connaissances. Je vous invite à contacter notre support : support@shopvite.fr ou au 0800 123 456."
"""


def build_user_prompt(question: str, context_chunks: list[dict]) -> str:
    context_text = "\n\n---\n\n".join(
        f"[Source : {c['source']}]\n{c['text']}" for c in context_chunks
    )
    return f"<contexte>\n{context_text}\n</contexte>\n\nQuestion du client : {question}"


def determine_confidence(chunks: list[dict]) -> Literal["high", "medium", "low"]:
    if not chunks:
        return "low"
    top = max(c["similarity"] for c in chunks)
    if top >= 0.35:
        return "high"
    elif top >= 0.10:
        return "medium"
    else:
        return "low"


def extract_sources(chunks: list[dict]) -> list[str]:
    seen, sources = set(), []
    for c in chunks:
        if c["source"] not in seen:
            seen.add(c["source"])
            sources.append(c["source"])
    return sources


def _call_mistral_http(user_prompt: str, api_key: str) -> str:
    """Appel direct à l'API Mistral via HTTP (sans SDK)."""
    payload = json.dumps({
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 500,
        "temperature": 0.1,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.mistral.ai/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return f"Erreur API Mistral ({e.code}) : {body[:200]}"
    except Exception as e:
        return f"Erreur réseau : {str(e)}"


def _demo_answer(question: str, chunks: list[dict], confidence: str) -> str:
    """Mode démo sans LLM : retourne le chunk le plus pertinent."""
    if not chunks or confidence == "low":
        return (
            "Je n'ai pas l'information nécessaire pour répondre à cette question "
            "dans ma base de connaissances. Je vous invite à contacter notre support : "
            "support@shopvite.fr ou au 0800 123 456."
        )
    best = chunks[0]
    excerpt = best["text"][:600] + ("..." if len(best["text"]) > 600 else "")
    return f"[MODE DÉMO]\n\n{excerpt}\n\n*(Source : {best['source']})*"


class Generator:
    def __init__(self):
        self.api_key = os.getenv("MISTRAL_API_KEY", "")
        self.backend = "mistral" if self.api_key else "demo"
        print(f"✓ Backend LLM : {self.backend}")

    def generate(self, question: str, context_chunks: list[dict]) -> dict:
        user_prompt = build_user_prompt(question, context_chunks)
        confidence = determine_confidence(context_chunks)
        sources = extract_sources(context_chunks)

        if self.backend == "mistral":
            answer = _call_mistral_http(user_prompt, self.api_key)
        else:
            answer = _demo_answer(question, context_chunks, confidence)

        return {
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
            "backend": self.backend,
        }
