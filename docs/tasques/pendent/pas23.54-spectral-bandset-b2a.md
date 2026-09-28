# Pas 23.54 — Skyglow físic — infraestructura espectral i benchmark B2a

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Introduir `SpectralBandSet`/`BandRadiance` sense fixar 8 bandes.

## Descripció funcional

Vectoritza la física en 1/2/4/8 bandes.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md) i documents especialitzats del dossier.
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- Fonts primàries de [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) quan el pas toca física o dades.

## Objectiu

Introduir `SpectralBandSet`/`BandRadiance` sense fixar 8 bandes.

## Dependències

**Depèn de:**
- [Pas 23.52](pas23.52-rayleigh-hg-b1a.md)

**En depenen:**
- [Pas 23.55](pas23.55-viirs-rsr.md)
- [Pas 23.60](pas23.60-optical-field.md)
- [Pas 23.63](pas23.63-gas-b4.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` com a namespace de domini existent, sense donar-ne per implementada la nova física.
- `backend/src/terralab3d/domain/atmosphere/`, `domain/horizon/`, `domain/terrain/` i adaptador DEM quan pertoqui.
- `frontend/src/bridge/`, `frontend/src/contracts/`, `AtmosphereRenderer.ts` i `skyShader.ts` només quan el pas arriba al frontend.

## Flux tècnic

compartir geometria i tiles entre bandes; vectors identificats per `bandSetId`.

## Errors, cancel·lació i recursos

- Resultats obsolets es descarten per revisió; cap càlcul llarg bloqueja el render thread.
- Fallbacks i dades absents es declaren amb procedència; no s'inventen valors.
- Risc principal: Duplicar ray-march per banda.
- Rollback: Conservar configuració d'una banda.

## Tasques

- [ ] Implementar només l'abast d'aquest pas amb contractes i unitats explícites.
- [ ] Afegir instrumentació i procedència necessàries.
- [ ] Integrar cancel·lació/revisions obsoletes quan hi hagi treball asíncron.
- [ ] Executar proves i benchmark indicats.
- [ ] Actualitzar inventari, README i evidències només segons estat real.

## Criteri de sortida

B2a `t(Nbands)` per 1/2/4/8. equivalència 1 banda, unitats i longituds de vector. El resultat queda reproduïble i no anticipa capacitats posteriors.

## Proves i evidències obligatòries

- [ ] equivalència 1 banda, unitats i longituds de vector.
- [ ] B2a `t(Nbands)` per 1/2/4/8.
- [ ] Guardar JSON/CSV/plots o golden data sota `docs/evidencies/pas23.54/` quan s'executi.
- [ ] Executar `tools/validate_docs.py` i regressions afectades abans de completar.

## Fora d'abast

RSR i priors SPD.

## Instrucció per a Codex

compartir geometria i tiles entre bandes; vectors identificats per `bandSetId`. No redissenyar decisions congelades del dossier; si una hipòtesi de benchmark falla, registrar l'evidència i proposar un ADR de substitució.

## Treball pendent

- [ ] Completar totes les tasques, proves i evidències abans de moure aquest document a `completat/`.