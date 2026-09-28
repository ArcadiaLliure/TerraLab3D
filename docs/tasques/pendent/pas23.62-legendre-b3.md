# Pas 23.62 — Skyglow físic — benchmark B3 de complexitat de fase

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Mesurar HG i Legendre 4/8/12/20 contra una referència independent.

## Descripció funcional

Converteix l'ordre L en decisió basada en error↔cost.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`01-especificacio-algorismes.md`](../../skyglow/01-especificacio-algorismes.md), [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) i [`09-incertesa-proveniencia.md`](../../skyglow/09-incertesa-proveniencia.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Mesurar HG i Legendre 4/8/12/20 contra una referència independent.

## Dependències

**Depèn de:**
- [Pas 23.61](pas23.61-phase-aerosol-library.md)

**En depenen:**
- [Pas 23.74](pas23.74-b7-homologacio-skyglow.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/atmosphere/` i `domain/light_pollution/`.
- `backend/src/terralab3d/infrastructure/adapters/` per fronteres externes.
- Bridge i escena existents només quan calgui publicar resultats.

## Flux tècnic

mateixa geometria/nodes → variants de fase → error angular/radiomètric + temps.

## Errors, cancel·lació i recursos

- Dades absents/corruptes es declaren; cap fallback silenciós.
- Dependències de tiles es registren durant la quadratura.
- Risc: Referència inadequada.
- Rollback: Mantenir L configurable.

## Tasques

- [ ] Implementar contractes i càlculs de l'abast.
- [ ] Afegir procedència i versions.
- [ ] Afegir proves numèriques.
- [ ] Executar benchmark indicat.
- [ ] Actualitzar evidències i inventari segons estat real.

## Criteri de sortida

reference phase d'ordre alt o taula Mie/mesurada. B3 complet HG/L4/L8/L12/L20. El resultat és reproduïble i no fixa candidats sense evidència.

## Proves i evidències obligatòries

- [ ] reference phase d'ordre alt o taula Mie/mesurada.
- [ ] B3 complet HG/L4/L8/L12/L20.
- [ ] Evidència sota `docs/evidencies/pas23.62/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

No fixa aerosol provider final.

## Instrucció per a Codex

mateixa geometria/nodes → variants de fase → error angular/radiomètric + temps. No traslladar detalls del proveïdor al `PropagationKernel`.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.