"""
main.py — API REST ShopVite FAQ Assistant.
Endpoints :
    POST /ask      → réponse RAG complète (si LLM dispo côté serveur)
    POST /retrieve → retourne les chunks pertinents pour un appel LLM côté client
    GET  /health   → statut de l'API
"""

import os, time
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.ingestion.ingestion import load_documents
from src.retrieval.vectorstore import index_chunks, retrieve, get_collection, CHROMA_PERSIST_DIR
from src.generation.generator import Generator

_generator = None
_startup_time = 0.0
_data_dir = os.getenv("DATA_DIR", "./data")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _generator, _startup_time
    t0 = time.time()
    print("\n═══════════════════════════════")
    print("  ShopVite FAQ Assistant")
    print("═══════════════════════════════")
    chunks = load_documents(_data_dir)
    index_chunks(chunks, persist_dir=CHROMA_PERSIST_DIR)
    _generator = Generator()
    _startup_time = time.time() - t0
    print(f"✓ API prête en {_startup_time:.1f}s")
    yield


app = FastAPI(title="ShopVite FAQ Assistant", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)

class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence: Literal["high", "medium", "low"]

class RetrieveResponse(BaseModel):
    chunks: list[dict]
    confidence: Literal["high", "medium", "low"]
    sources: list[str]

class HealthResponse(BaseModel):
    status: str
    chunks_indexed: int
    llm_backend: str


@app.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest):
    if _generator is None:
        raise HTTPException(503, "Service non initialisé.")
    try:
        ctx = retrieve(body.question)
        result = _generator.generate(question=body.question, context_chunks=ctx)
        return AskResponse(answer=result["answer"], sources=result["sources"], confidence=result["confidence"])
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_chunks(body: AskRequest):
    """Retourne les chunks pertinents — pour un appel LLM côté client (browser)."""
    if _generator is None:
        raise HTTPException(503, "Service non initialisé.")
    try:
        from src.generation.generator import determine_confidence, extract_sources
        ctx = retrieve(body.question)
        return RetrieveResponse(
            chunks=ctx,
            confidence=determine_confidence(ctx),
            sources=extract_sources(ctx)
        )
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/health", response_model=HealthResponse)
async def health():
    try:
        nb = get_collection(CHROMA_PERSIST_DIR).count()
    except:
        nb = -1
    return HealthResponse(
        status="ok",
        chunks_indexed=nb,
        llm_backend=_generator.backend if _generator else "non initialisé",
    )
