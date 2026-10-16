# Pas 7.11 — Skyglow físic — OpticalField tiled i dependències

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Crear un camp òptic 3D+temps versionat i registrar tiles durant la quadratura.

## Descripció funcional

Base per atmosfera variable i cache selectiva.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`01-especificacio-algorismes.md`](../../skyglow/01-especificacio-algorismes.md), [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) i [`09-incertesa-proveniencia.md`](../../skyglow/09-incertesa-proveniencia.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Crear un camp òptic 3D+temps versionat i registrar tiles durant la quadratura.

## Dependències

**Depèn de:**
- [Pas 7.5](pas7.5-spectral-bandset-b2a.md)

**En depenen:**
- [Pas 7.12](pas7.12-phase-aerosol-library.md)
- [Pas 7.14](pas7.14-gas-b4.md)
- [Pas 7.15](pas7.15-atmos-provider-standard.md)
- [Pas 7.18](pas7.18-cache-error-based.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/atmosphere/` i `domain/light_pollution/`.
- `backend/src/terralab3d/infrastructure/adapters/` per fronteres externes.
- Bridge i escena existents només quan calgui publicar resultats.

## Flux tècnic

OpticalState → tiles/capes versionats → segmentació LOS → dependency set en la mateixa visita.

## Errors, cancel·lació i recursos

- Dades absents/corruptes es declaren; cap fallback silenciós.
- Dependències de tiles es registren durant la quadratura.
- Risc: Granularitat massa fina.
- Rollback: Tiles més grans sense canviar API.

## Tasques

- [ ] Implementar contractes i càlculs de l'abast.
- [ ] Afegir procedència i versions.
- [ ] Afegir proves numèriques.
- [ ] Executar benchmark indicat.
- [ ] Actualitzar evidències i inventari segons estat real.

## Criteri de sortida

travessa múltiples tiles, versions i exactitud de dependències. B0/B1 amb 1/2/8 tiles. El resultat és reproduïble i no fixa candidats sense evidència.

## Proves i evidències obligatòries

- [ ] travessa múltiples tiles, versions i exactitud de dependències.
- [ ] B0/B1 amb 1/2/8 tiles.
- [ ] Evidència sota `docs/evidencies/pas7.11/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Providers meteorològics reals.

## Instrucció per a Codex

OpticalState → tiles/capes versionats → segmentació LOS → dependency set en la mateixa visita. No traslladar detalls del proveïdor al `PropagationKernel`.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.