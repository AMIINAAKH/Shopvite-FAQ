# Réflexion technique — ShopVite FAQ Assistant

## Justification du prompt engineering

Le system prompt repose sur cinq décisions délibérées. Premièrement, **une identité explicite** ("assistant virtuel de ShopVite") ancre les réponses dans un contexte métier précis et limite la dérive vers des connaissances générales. Deuxièmement, des **règles numérotées** plutôt qu'un paragraphe narratif : les LLMs instruction-tuned suivent mieux des contraintes ordonnées et explicites. Troisièmement, des **few-shot examples** (un exemple in-scope, un out-of-scope) constituent le garde-fou anti-hallucination le plus efficace — le modèle "voit" exactement ce qu'on attend dans les deux cas limites. Quatrièmement, l'**encapsulation du contexte dans des balises `<contexte>`** permet au modèle d'identifier clairement quelle partie du prompt est source de vérité versus instruction, technique recommandée par Mistral et Anthropic. Cinquièmement, l'obligation de **citer la source** en fin de réponse force le modèle à rester ancré dans les documents et offre une traçabilité immédiate à l'utilisateur.

---

## Ce que je ferais différemment avec plus de temps

- **Embeddings neuronaux** : remplacer le TF-IDF par `intfloat/multilingual-e5-large` (MTEB state-of-the-art français) pour capturer la sémantique — ex. "me faire rembourser" = "politique de retour".
- **Reranking** : ajouter un cross-encoder après le retrieval pour re-classer les chunks et améliorer la précision du top-1.
- **Hybrid search** : combiner recherche vectorielle et BM25 via rank fusion — crucial pour les correspondances exactes (numéro de produit, prix précis).
- **Évaluation RAGAS complète** : implémenter `faithfulness`, `answer_relevancy` et `context_recall` sur 50+ questions pour calibrer les seuils de confiance de façon rigoureuse.
- **Streaming** : afficher les tokens au fur et à mesure pour une meilleure expérience utilisateur.

---

## Limitation identifiée du système actuel

Le moteur TF-IDF ne capture pas la **similarité sémantique** : "comment me faire rembourser ?" ne matche pas bien avec le chunk "politique de retour" car ils ne partagent pas les mêmes tokens. Un embedding neuronal multilingue résoudrait ce problème. Le TF-IDF a été choisi pour une démonstration 100 % offline sans dépendance réseau, mais il constitue le principal point d'amélioration du pipeline.
