# Sources de données — Corpus ShopVite

## Origine des documents

Ce corpus a été créé de toutes pièces pour simuler la documentation réelle d'une boutique e-commerce d'électronique (ShopVite, nom fictif). Tous les documents sont des **créations originales** rédigées pour ce projet.

## Liste des fichiers

| Fichier | Format | Contenu | Nb tokens estimé |
|---|---|---|---|
| `politique_retours.md` | Markdown | Politique de retour complète : délais, conditions, procédure, remboursement | ~450 |
| `guide_livraison.md` | Markdown | Modes de livraison, délais, zones géographiques, cas particuliers | ~520 |
| `garantie_sav.md` | Markdown | Garantie légale, garantie constructeur par catégorie, procédure SAV, extensions | ~580 |
| `catalogue_produits.json` | JSON | Catalogue structuré : smartphones, PC portables, TV — fiches produit et comparatifs | ~900 |
| `cgv_paiement.md` | Markdown | Moyens de paiement, paiement en plusieurs fois, fidélité, RGPD, contacts | ~490 |

## Justification du corpus

- **Diversité des formats** : Markdown (texte structuré) + JSON (données structurées), afin de tester la robustesse du chunking sur des structures différentes.
- **Couverture thématique** : Les 5 fichiers couvrent les questions les plus fréquentes en support e-commerce (retours, livraison, garantie, produits, paiement).
- **Taille maîtrisée** : Corpus volontairement compact (~3000 tokens) pour permettre une démonstration rapide sans dépendre d'une infrastructure lourde.
- **Données fictives cohérentes** : Tous les prix, délais et caractéristiques sont plausibles et cohérents entre eux.

## Alternative avec datasets publics

Si vous souhaitez tester avec un corpus plus large, vous pouvez utiliser :
- [E-Commerce FAQ (Kaggle)](https://www.kaggle.com/datasets) — ~15 MB de FAQ génériques
- [Amazon QA (Hugging Face)](https://huggingface.co/datasets) — ~1.2 GB de Q/R produits Amazon
