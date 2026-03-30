# ShopVite FAQ Assistant — Pipeline RAG

> Assistant IA de support client pour la boutique e-commerce ShopVite.  
> Répond automatiquement aux questions clients à partir de la documentation officielle — sans inventer d'informations.

---

## Architecture du pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                   ShopVite FAQ Assistant                     │
│                                                             │
│  ┌──────────┐   ┌───────────┐   ┌──────────────────────┐   │
│  │  data/   │──▶│ Chunking  │──▶│  Vector Store        │   │
│  │ .md .json│   │ sémantique│   │  TF-IDF (local)      │   │
│  └──────────┘   └───────────┘   └──────────┬───────────┘   │
│       ①               ②                    │ ③ Retrieval   │
│                                            ▼               │
│  ┌──────────┐   ┌───────────┐   ┌──────────────────────┐   │
│  │ Question │──▶│ FastAPI   │──▶│  top-k chunks        │   │
│  │ client   │   │ POST /ask │   │  + contexte injecté  │   │
│  └──────────┘   └───────────┘   └──────────┬───────────┘   │
│                                            │ ④ Génération  │
│  ┌──────────┐                  ┌───────────▼───────────┐   │
│  │ Réponse  │◀─────────────────│  Mistral small-latest │   │
│  │ + sources│                  │  (system prompt RAG)  │   │
│  └──────────┘                  └───────────────────────┘   │
│       ⑤ API REST                                           │
└─────────────────────────────────────────────────────────────┘

① Ingestion   — chargement multi-format (.md + .json), chunking sémantique
② Vectorisation — index TF-IDF cosinus, persisté sur disque
③ Retrieval   — top-k=4 chunks les plus similaires à la requête
④ Génération  — contexte injecté dans Mistral via system prompt RAG
⑤ Exposition  — API REST FastAPI : POST /ask  |  GET /health
```

---

## Setup en 3 commandes

```bash
# 1. Configurer l'environnement
cp .env.example .env          # puis renseigner MISTRAL_API_KEY

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Démarrer l'API
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

**Interface de démo** : ouvrir `docs/demo.html` dans un navigateur.  
**Documentation Swagger** : `http://localhost:8000/docs`

### Avec Docker

```bash
docker build -t shopvite-rag .
docker run -p 8000:8000 -e MISTRAL_API_KEY=votre_clé shopvite-rag
```

---

## Choix techniques justifiés

| Composant | Choix | Justification |
|---|---|---|
| **Framework API** | FastAPI | Async natif, validation Pydantic, Swagger auto-généré |
| **Vector store** | TF-IDF local (pickle) | Zéro dépendance réseau, pas de compte requis, suffisant pour un corpus compact |
| **LLM** | Mistral `small-latest` | Excellent support du français, API abordable, latence < 2s |
| **Chunking** | Par sections Markdown | Préserve la cohérence sémantique vs. découpage fixe en tokens |
| **Déploiement** | Docker multi-stage | Image légère, reproductible, variables d'env documentées |

> **Note production** : remplacer TF-IDF par `intfloat/multilingual-e5-large` + ChromaDB pour une meilleure qualité sémantique.

---

## Exemples de requêtes avec résultats

### Question in-scope — politique de retour

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Quelle est la politique de retour ?"}'
```

```json
{
  "answer": "Vous disposez de 30 jours calendaires à compter de la réception pour retourner tout produit, sans justification requise. Pour un produit défectueux, ce délai est étendu à 60 jours. Le remboursement est effectué sous 5 à 10 jours ouvrés. (Source : politique_retours.md)",
  "sources": ["politique_retours.md"],
  "confidence": "high"
}
```

### Question in-scope — livraison express

```bash
curl -X POST http://localhost:8000/ask \
  -d '{"question": "Combien coûte la livraison express ?"}'
```

```json
{
  "answer": "La livraison express via Chronopost est disponible à 9,99 €, avec une livraison en 24h à 48h. La livraison standard coûte 4,99 € (3 à 5 jours) et est gratuite dès 50 € d'achat. (Source : guide_livraison.md)",
  "sources": ["guide_livraison.md"],
  "confidence": "medium"
}
```

### Question hors-scope

```bash
curl -X POST http://localhost:8000/ask \
  -d '{"question": "Quelle est la météo à Paris demain ?"}'
```

```json
{
  "answer": "Je n'ai pas l'information nécessaire pour répondre à cette question dans ma base de connaissances. Je vous invite à contacter notre support : support@shopvite.fr ou au 0800 123 456.",
  "sources": [],
  "confidence": "low"
}
```

### Santé de l'API

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "chunks_indexed": 46,
  "llm_backend": "mistral"
}
```

---

## Structure du projet

```
shopvite-rag/
├── src/
│   ├── ingestion/ingestion.py     # Chargement et chunking des documents
│   ├── retrieval/vectorstore.py   # Index TF-IDF + retrieval
│   ├── generation/generator.py    # System prompt + appel Mistral
│   └── api/main.py                # FastAPI : /ask, /retrieve, /health
├── data/
│   ├── politique_retours.md
│   ├── guide_livraison.md
│   ├── garantie_sav.md
│   ├── catalogue_produits.json
│   ├── cgv_paiement.md
│   └── data_sources.md
├── eval/
│   └── evaluate.py                # Évaluation sur 10 questions
├── docs/
│   └── demo.html                  # Interface de démonstration
├── Dockerfile
├── requirements.txt
├── .env.example
└── reflection.md
```

---

## Variables d'environnement

| Variable | Description | Requis |
|---|---|---|
| `MISTRAL_API_KEY` | Clé API Mistral (console.mistral.ai) | ✅ |
| `DATA_DIR` | Répertoire des documents | optionnel (défaut : `./data`) |
| `CHROMA_PERSIST_DIR` | Répertoire de persistance de l'index | optionnel (défaut : `./chroma_db`) |
| `PORT` | Port du serveur | optionnel (défaut : `8000`) |
