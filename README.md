# TerraLab3D — esquelet arquitectònic ampliat

TerraLab3D és un projecte independent inspirat en totes les capacitats visibles de TerraLab. No copia la seva arquitectura d’execució: conserva TerraLab com a font de comportament, fórmules, datasets, fixtures i criteris de paritat.

## Objectiu de l’esquelet

- Acollir tota la lògica científica en paquets funcionals del domini.
- Separar models, càlculs purs, serveis de domini, casos d’ús, ports, adaptadors i presentació.
- Mantenir una escena Three.js persistent amb recursos GPU versionats.
- Enviar deltes petits i recursos binaris, mai catàlegs sencers per cada frame.
- Permetre arribar, de manera incremental, a la paritat funcional amb TerraLab.

## Espai de treball

```text
backend/       Domini científic, aplicació, escena neutral i adaptadors
frontend/      UI TypeScript, bridge i adaptador Three.js persistent
contracts/     Esquemes canònics del límit entre processos
scripts/       Validacions estructurals i futures eines de desenvolupament
docs/          Arquitectura, mapa de migració i pla d’implementació
```

## Regla arquitectònica central

```text
Entrada d’usuari → Comanda d’aplicació → Estat de domini
→ Delta de escena → Adaptador Three.js → GPU
```

La càmera, la interpolació visual i la rotació contínua de la volta celeste viuen al frontend. La ciència autoritativa, la selecció de dades i la preparació de recursos viuen al backend. Un canvi d’un segon no retransmet Gaia, terreny ni textures.

## Validació de l’esquelet

```bash
python tools/validate_skeleton.py
python -m compileall -q backend/src
PYTHONPATH=backend/src python -c "import terralab3d"
npx tsc -p frontend/tsconfig.json --noEmit
```

## Documents principals

- `docs/architecture.md`: capes, dependències i fluxos.
- `docs/terralab-to-terralab3d-map.md`: transformació funcional des de TerraLab.
- `docs/pla-implementacio-pas-a-pas.md`: implementació completa fins a la paritat funcional.
- `docs/inventari-funcional.md`: inventari de capacitats que l’esquelet ha d’acollir.
