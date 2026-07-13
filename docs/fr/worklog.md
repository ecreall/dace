# Fil de l'eau

Journal au fil de l'eau des travaux sur ce dépôt, du plus récent au plus ancien.
English version: [`../en/worklog.md`](../en/worklog.md).

## 2026-07-13

- Fork de `ecreall/dace` vers `michaellaunay/dace` ; reprise de la maintenance
  par Michaël Launay (Logikascium).
- Conversion de `README.rst` et `CHANGES.rst` en Markdown ; README réécrit avec
  le statut du dépôt et la feuille de route de modernisation.
- Mise à jour des métadonnées de build (`setup.py` : URLs du fork, champ
  mainteneur, description longue en Markdown) ; ajout d'un `pyproject.toml`
  minimal (PEP 518) ; mise à jour du `MANIFEST.in`.
- Ajout de `constraints-legacy.txt` (épinglages de dépendances 2017 connus pour
  fonctionner) et d'un workflow de CI legacy best-effort (`python:3.6-buster`).
- Mise en place de la structure de documentation bilingue (`docs/en`,
  `docs/fr`) et de ce fil de l'eau.
- Exclusion des artefacts de livraison (`*.patch`, `*.diff`, archives) et des
  résidus de `git apply` via `.gitignore` ; suppression de
  `dace-docs-structure.patch`, commité par erreur.
