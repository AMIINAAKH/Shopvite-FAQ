"""
ingestion.py — Chargement et découpage des documents du corpus ShopVite.

Supporte les formats : Markdown (.md), JSON (.json), PDF (.pdf), TXT (.txt)
Stratégie de chunking : découpage par blocs sémantiques avec overlap.
"""

import json
import re
from pathlib import Path
from typing import Iterator


# ── Configuration du chunking ──────────────────────────────────────────────────
CHUNK_SIZE = 400        # Taille cible d'un chunk (en caractères)
CHUNK_OVERLAP = 80      # Chevauchement entre chunks consécutifs


def load_documents(data_dir: str) -> list[dict]:
    """
    Charge tous les documents du répertoire data/ et retourne une liste de chunks.

    Chaque chunk est un dict :
        { "text": str, "source": str, "chunk_id": str }
    """
    data_path = Path(data_dir)
    all_chunks: list[dict] = []

    for filepath in sorted(data_path.iterdir()):
        if filepath.suffix == ".md":
            raw_text = filepath.read_text(encoding="utf-8")
            chunks = chunk_markdown(raw_text, filepath.name)
        elif filepath.suffix == ".json":
            raw_text = filepath.read_text(encoding="utf-8")
            chunks = chunk_json(raw_text, filepath.name)
        elif filepath.suffix in (".txt", ".pdf"):
            # PDF nécessite pdfminer/pypdf ; ici on lit le texte brut
            raw_text = filepath.read_text(encoding="utf-8", errors="ignore")
            chunks = chunk_text(raw_text, filepath.name)
        else:
            continue  # Ignorer les fichiers non supportés

        all_chunks.extend(chunks)
        print(f"  ✓ {filepath.name} → {len(chunks)} chunks")

    print(f"\nTotal : {len(all_chunks)} chunks ingérés depuis {data_dir}")
    return all_chunks


# ── Chunking par stratégie ──────────────────────────────────────────────────────

def chunk_markdown(text: str, source: str) -> list[dict]:
    """
    Découpe un document Markdown en respectant la structure des sections (## titres).
    Chaque section de titre est conservée comme unité sémantique.
    Si une section est trop longue, elle est re-découpée avec overlap.
    """
    # Découpage par titres Markdown (## ou ###)
    sections = re.split(r"\n(?=#{1,3} )", text)
    chunks = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Si la section est dans la limite, on la garde entière
        if len(section) <= CHUNK_SIZE * 1.5:
            chunks.append(section)
        else:
            # Re-découpage par paragraphes avec overlap
            chunks.extend(_split_with_overlap(section))

    return _format_chunks(chunks, source)


def chunk_json(text: str, source: str) -> list[dict]:
    """
    Convertit un JSON structuré en chunks textuels lisibles.
    Chaque entité de premier niveau (produit, politique, etc.) devient un chunk.
    """
    data = json.loads(text)
    raw_chunks = list(_flatten_json(data))
    return _format_chunks(raw_chunks, source)


def chunk_text(text: str, source: str) -> list[dict]:
    """Découpage générique pour TXT/PDF bruts."""
    chunks = _split_with_overlap(text)
    return _format_chunks(chunks, source)


# ── Utilitaires internes ────────────────────────────────────────────────────────

def _split_with_overlap(text: str) -> list[str]:
    """Découpe un texte en chunks de CHUNK_SIZE avec CHUNK_OVERLAP de chevauchement."""
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        current.append(word)
        current_len += len(word) + 1

        if current_len >= CHUNK_SIZE:
            chunks.append(" ".join(current))
            # Garder les derniers mots pour l'overlap
            overlap_words = current[-(CHUNK_OVERLAP // 6):]
            current = overlap_words
            current_len = sum(len(w) + 1 for w in current)

    if current:
        chunks.append(" ".join(current))

    return chunks


def _flatten_json(obj, prefix: str = "", depth: int = 0) -> Iterator[str]:
    """
    Parcourt récursivement un dict/list JSON et génère des blocs textuels
    lisibles pour chaque entité significative.
    """
    if depth > 4:
        return

    if isinstance(obj, dict):
        # Cas d'un produit avec "nom" et "caracteristiques" → chunk unique
        if "nom" in obj and isinstance(obj.get("caracteristiques"), dict):
            lines = [f"Produit : {obj.get('nom', '')}"]
            if "marque" in obj:
                lines.append(f"Marque : {obj['marque']}")
            if "prix" in obj:
                lines.append(f"Prix : {obj['prix']} €")
            if "stock" in obj:
                lines.append(f"Disponibilité : {obj['stock']}")
            carac = obj["caracteristiques"]
            for k, v in carac.items():
                lines.append(f"  {k.replace('_', ' ').capitalize()} : {v}")
            if "points_forts" in obj:
                lines.append("Points forts : " + ", ".join(obj["points_forts"]))
            if "points_faibles" in obj:
                lines.append("Points faibles : " + ", ".join(obj["points_faibles"]))
            if "note_clients" in obj:
                lines.append(f"Note clients : {obj['note_clients']}/5 ({obj.get('nb_avis', 0)} avis)")
            yield "\n".join(lines)
        else:
            for key, value in obj.items():
                yield from _flatten_json(value, prefix=key, depth=depth + 1)

    elif isinstance(obj, list):
        for item in obj:
            yield from _flatten_json(item, prefix=prefix, depth=depth + 1)

    elif isinstance(obj, str) and len(obj) > 80:
        yield f"{prefix} : {obj}" if prefix else obj


def _format_chunks(raw: list[str], source: str) -> list[dict]:
    """Attache les métadonnées (source, chunk_id) à chaque chunk brut."""
    result = []
    for i, text in enumerate(raw):
        text = text.strip()
        if len(text) < 30:  # Ignorer les micro-fragments inutiles
            continue
        result.append({
            "text": text,
            "source": source,
            "chunk_id": f"{source}::{i}",
        })
    return result
