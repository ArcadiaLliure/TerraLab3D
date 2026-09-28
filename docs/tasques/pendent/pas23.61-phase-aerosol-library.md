# Pas 23.61 — Skyglow físic — PhaseFunction unificada i AerosolOpticsLibrary mínima

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Unificar la fase i preparar la biblioteca aerosol amb HG com a fallback.

## Descripció funcional

El kernel consumeix una representació comuna independent de l'origen.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`01-especificacio-algorismes.md`](../../skyglow/01-especificacio-algorismes.md), [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) i [`09-incertesa-proveniencia.md`](../../skyglow/09-incertesa-proveniencia.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Unificar la fase i preparar la biblioteca aerosol amb HG com a fallback.

## Dependències

**Depèn de:**
- [Pas 23.52](pas23.52-rayleigh-hg-b1a.md)
- [Pas 23.60](pas23.60-optical-field.md)

**En depenen:**
- [Pas 23.62](pas23.62-legendre-b3.md)
- [Pas 23.64](pas23.64-atmos-provider-standard.md)
- [Pas 23.73](pas23.73-clouds-b6.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/atmosphere/` i `domain/light_pollution/`.
- `backend/src/terralab3d/infrastructure/adapters/` per fronteres externes.
- Bridge i escena existents només quan calgui publicar resultats.

## Flux tècnic

model/taula/HG → coeficients Legendre normalitzats → `PhaseFunction` + provenance.

## Errors, cancel·lació i recursos

- Dades absents/corruptes es declaren; cap fallback silenciós.
- Dependències de tiles es registren durant la quadratura.
- Risc: Truncació amb lobes negatius.
- Rollback: HG directe darrere del mateix contracte.

## Tasques

- [ ] Implementar contractes i càlculs de l'abast.
- [ ] Afegir procedència i versions.
- [ ] Afegir proves numèriques.
- [ ] Executar benchmark indicat.
- [ ] Actualitzar evidències i inventari segons estat real.

## Criteri de sortida

HG directe vs expansió alta, cas isòtrop i normalització. Microbenchmark de fase. El resultat és reproduïble i no fixa candidats sense evidència.

## Proves i evidències obligatòries

- [ ] HG directe vs expansió alta, cas isòtrop i normalització.
- [ ] Microbenchmark de fase.
- [ ] Evidència sota `docs/evidencies/pas23.61/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Selecció definitiva d'aerosols.

## Instrucció per a Codex

model/taula/HG → coeficients Legendre normalitzats → `PhaseFunction` + provenance. No traslladar detalls del proveïdor al `PropagationKernel`.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.