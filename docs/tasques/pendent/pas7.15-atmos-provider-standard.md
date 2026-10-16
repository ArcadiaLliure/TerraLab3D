# Pas 7.15 — Skyglow físic — AtmosphericOpticsProvider amb atmosfera estàndard

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Implementar provider fallback complet amb procedència per camp.

## Descripció funcional

Permet executar el kernel sense xarxa ni reanàlisi.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`01-especificacio-algorismes.md`](../../skyglow/01-especificacio-algorismes.md), [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) i [`09-incertesa-proveniencia.md`](../../skyglow/09-incertesa-proveniencia.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Implementar provider fallback complet amb procedència per camp.

## Dependències

**Depèn de:**
- [Pas 7.11](pas7.11-optical-field.md)
- [Pas 7.12](pas7.12-phase-aerosol-library.md)
- [Pas 7.14](pas7.14-gas-b4.md)

**En depenen:**
- [Pas 7.16](pas7.16-atmos-provider-era5-cams.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/atmosphere/` i `domain/light_pollution/`.
- `backend/src/terralab3d/infrastructure/adapters/` per fronteres externes.
- Bridge i escena existents només quan calgui publicar resultats.

## Flux tècnic

perfil estàndard versionat → OpticalParameter per camp → OpticalState → OpticalField.

## Errors, cancel·lació i recursos

- Dades absents/corruptes es declaren; cap fallback silenciós.
- Dependències de tiles es registren durant la quadratura.
- Risc: Confondre fallback amb observació.
- Rollback: Provider unavailable en lloc de dades falses.

## Tasques

- [ ] Implementar contractes i càlculs de l'abast.
- [ ] Afegir procedència i versions.
- [ ] Afegir proves numèriques.
- [ ] Executar benchmark indicat.
- [ ] Actualitzar evidències i inventari segons estat real.

## Criteri de sortida

offline determinista, interpolació vertical i provenance. Resolve throughput i build OpticalField. El resultat és reproduïble i no fixa candidats sense evidència.

## Proves i evidències obligatòries

- [ ] offline determinista, interpolació vertical i provenance.
- [ ] Resolve throughput i build OpticalField.
- [ ] Evidència sota `docs/evidencies/pas7.15/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

ERA5/CAMS/live.

## Instrucció per a Codex

perfil estàndard versionat → OpticalParameter per camp → OpticalState → OpticalField. No traslladar detalls del proveïdor al `PropagationKernel`.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.