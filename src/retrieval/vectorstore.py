"""
vectorstore.py — Embeddings et indexation locale (TF-IDF, 100% offline).

En production, remplacer par sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
(décommenter dans requirements.txt) pour une meilleure qualité sémantique.
"""

import json, math, os, pickle, re
from collections import Counter

TOP_K = 4
CHROMA_PERSIST_DIR = "./chroma_db"


def _tokenize(text: str) -> list[str]:
    STOPWORDS = {
        "le","la","les","de","du","des","un","une","et","en","à","au","aux",
        "pour","par","sur","est","sont","avec","dans","qui","que","ou","pas",
        "ne","se","si","ce","cet","cette","the","a","an","of","is","in","to",
        "for","on","at","be","il","elle","ils","elles","nous","vous","je","tu",
        "mon","ma","mes","votre","vos","leur","leurs","son","sa","ses","tout",
        "tous","toute","toutes","plus","mais","car","on","se","même","très",
    }
    tokens = re.findall(r"[a-záàâéèêëïîôùûüçœæ0-9]+", text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def _cosine(a: dict, b: dict) -> float:
    dot = sum(a.get(t, 0.0) * b.get(t, 0.0) for t in a)
    norm_a = math.sqrt(sum(v*v for v in a.values()))
    norm_b = math.sqrt(sum(v*v for v in b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


class LocalVectorStore:
    def __init__(self):
        self.chunks: list[dict] = []
        self.tfidf: list[dict] = []
        self.idf: dict[str, float] = {}

    def fit(self, chunks: list[dict]) -> None:
        self.chunks = chunks
        tokenized = [_tokenize(c["text"]) for c in chunks]
        N = len(chunks)
        df: Counter = Counter()
        for tokens in tokenized:
            for t in set(tokens):
                df[t] += 1
        self.idf = {t: math.log((N+1)/(cnt+1))+1.0 for t, cnt in df.items()}
        self.tfidf = []
        for tokens in tokenized:
            tf = Counter(tokens)
            total = max(len(tokens), 1)
            self.tfidf.append({t: (c/total)*self.idf.get(t,0.) for t,c in tf.items()})

    def query(self, text: str, k: int = TOP_K) -> list[dict]:
        q_tok = _tokenize(text)
        q_tf = Counter(q_tok)
        total = max(len(q_tok), 1)
        q_vec = {t: (c/total)*self.idf.get(t,0.) for t,c in q_tf.items()}
        scores = sorted(
            [(i, _cosine(q_vec, dv)) for i, dv in enumerate(self.tfidf)],
            key=lambda x: x[1], reverse=True
        )
        return [
            {"text": self.chunks[i]["text"], "source": self.chunks[i]["source"],
             "distance": round(1-s,4), "similarity": round(s,4)}
            for i,s in scores[:k]
        ]

    def count(self) -> int:
        return len(self.chunks)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load(path: str) -> "LocalVectorStore":
        with open(path, "rb") as f:
            return pickle.load(f)


_store: LocalVectorStore | None = None


def get_collection(persist_dir: str = CHROMA_PERSIST_DIR) -> LocalVectorStore:
    global _store
    if _store is not None:
        return _store
    path = os.path.join(persist_dir, "index.pkl")
    _store = LocalVectorStore.load(path) if os.path.exists(path) else LocalVectorStore()
    return _store


def index_chunks(chunks: list[dict], persist_dir: str = CHROMA_PERSIST_DIR) -> None:
    global _store
    path = os.path.join(persist_dir, "index.pkl")
    if os.path.exists(path):
        _store = LocalVectorStore.load(path)
        print(f"✓ Index déjà chargé ({_store.count()} chunks). Skip.")
        return
    print(f"Indexation TF-IDF de {len(chunks)} chunks...")
    _store = LocalVectorStore()
    _store.fit(chunks)
    _store.save(path)
    print(f"✓ Index sauvegardé ({_store.count()} chunks).")


def retrieve(query: str, k: int = TOP_K, persist_dir: str = CHROMA_PERSIST_DIR) -> list[dict]:
    store = get_collection(persist_dir)
    if store.count() == 0:
        raise RuntimeError("Index vide — lancez d'abord l'ingestion.")
    return store.query(query, k=k)
