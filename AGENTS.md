# Règles pour les agents (py2x)

- Lire `README.md` puis `docs/ARCHITECTURE.md`.
- Garantie centrale : sortie identique à Python en C++ et en Kotlin. Ce qui ne peut pas l'être est **refusé** (`Unsupported`), jamais approximé.
- Avant tout commit : `python -m unittest discover -s tests` ; pour un changement d'émetteur/runtime, aussi `PY2X_COMPILE=cpp,kotlin`.
- Chaque changement de comportement met à jour `docs/` (SUPPORTED.md, USAGE.md…) dans le même commit.
- Pousser chaque changement sur GitHub avec un message clair. Commit de docs seule : `[skip ci]`.
- Pas de dépendances externes.
