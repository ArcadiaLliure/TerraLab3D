# Pas 23.63 — Skyglow físic — GasAbsorptionModel i benchmark B4

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Afegir absorció O3/H2O/O2 via LUT efectiva preservant transmitància.

## Descripció funcional

Evita `β_abs=0` i `exp(-mean τ)`.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md).
- [`01-especificacio-algorismes.md`](../../skyglow/01-especificacio-algorismes.md), [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) i [`09-incertesa-proveniencia.md`](../../skyglow/09-incertesa-proveniencia.md).
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md).

## Objectiu

Afegir absorció O3/H2O/O2 via LUT efectiva preservant transmitància.

## Dependències

**Depèn de:**
- [Pas 23.54](pas23.54-spectral-bandset-b2a.md)
- [Pas 23.60](pas23.60-optical-field.md)

**En depenen:**
- [Pas 23.64](pas23.64-atmos-provider-standard.md)
- [Pas 23.73](pas23.73-clouds-b6.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/atmosphere/` i `domain/light_pollution/`.
- `backend/src/terralab3d/infrastructure/adapters/` per fronteres externes.
- Bridge i escena existents només quan calgui publicar resultats.

## Flux tècnic

HITRAN/LOWTRAN offline → LUT `T_eff(k,f,T,p,column)` → lookup vectoritzat al kernel.

## Errors, cancel·lació i recursos

- Dades absents/corruptes es declaren; cap fallback silenciós.
- Dependències de tiles es registren durant la quadratura.
- Risc: Llicència de derivats i resolució insuficient.
- Rollback: LUT mínima pròpia amb font permesa.

## Tasques

- [ ] Implementar contractes i càlculs de l'abast.
- [ ] Afegir procedència i versions.
- [ ] Afegir proves numèriques.
- [ ] Executar benchmark indicat.
- [ ] Actualitzar evidències i inventari segons estat real.

## Criteri de sortida

Jensen sanity, comparació espectral fina i interpolació LUT. B4 cost incremental. El resultat és reproduïble i no fixa candidats sense evidència.

## Proves i evidències obligatòries

- [ ] Jensen sanity, comparació espectral fina i interpolació LUT.
- [ ] B4 cost incremental.
- [ ] Evidència sota `docs/evidencies/pas23.63/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd.

## Fora d'abast

Line-by-line runtime.

## Instrucció per a Codex

HITRAN/LOWTRAN offline → LUT `T_eff(k,f,T,p,column)` → lookup vectoritzat al kernel. No traslladar detalls del proveïdor al `PropagationKernel`.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure el pas a `completat/`.