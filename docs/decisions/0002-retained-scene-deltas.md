# ADR 0002 — Escena retinguda i deltes

## Decisió

El frontend conserva entitats i recursos. El backend publica només diferències entre generacions; els snapshots complets són només d’arrencada o recuperació.

## Conseqüències

Canviar la càmera no reconstrueix l’escena, i canviar un segon no retransmet catàlegs, textures ni terreny.
