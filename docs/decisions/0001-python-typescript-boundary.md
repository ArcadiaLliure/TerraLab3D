# ADR 0001 — Frontera Python / TypeScript

## Decisió

Python és propietari de la ciència i l’estat de producte. TypeScript és propietari de la UI, la càmera, l’escena Three.js persistent i els recursos GPU.

## Conseqüències

- Les dades grans travessen la frontera com recursos binaris versionats.
- Les actualitzacions normals són deltes petits.
- TypeScript no calcula efemèrides ni consulta datasets científics.
