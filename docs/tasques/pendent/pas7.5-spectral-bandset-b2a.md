# Pas 7.5 — Skyglow físic — infraestructura espectral configurable i proves B2a

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Introduir `SpectralBandSet`/`BandRadiance` amb `spectralBandCount` i límits/ponderacions versionats, sense nombre fix.

## Descripció funcional

Vectoritza la física amb el nombre de bandes seleccionat per configuració, sense nombre fix ni benchmark per triar-lo.

## Fonts a consultar

- [`docs/skyglow/README.md`](../../skyglow/README.md) i documents especialitzats del dossier.
- [`docs/normes-arquitectura.md`](../../normes-arquitectura.md) i [`docs/inventari-funcional.md`](../../inventari-funcional.md).
- Fonts primàries de [`04-justificacio-cientifica.md`](../../skyglow/04-justificacio-cientifica.md) quan el pas toca física o dades.

## Objectiu

Introduir `SpectralBandSet`/`BandRadiance` sense fixar 8 bandes.

## Dependències

**Depèn de:**
- [Pas 7.3](pas7.3-rayleigh-hg-b1a.md)

**En depenen:**
- [Pas 7.6](pas7.6-viirs-rsr.md)
- [Pas 7.11](pas7.11-optical-field.md)
- [Pas 7.14](pas7.14-gas-b4.md)

## Codi existent a reutilitzar

- `backend/src/terralab3d/domain/light_pollution/` com a namespace de domini existent, sense donar-ne per implementada la nova física.
- `backend/src/terralab3d/domain/atmosphere/`, `domain/horizon/`, `domain/terrain/` i adaptador DEM quan pertoqui.
- `frontend/src/bridge/`, `frontend/src/contracts/`, `AtmosphereRenderer.ts` i `skyShader.ts` només quan el pas arriba al frontend.

## Flux tècnic

compartir geometria i tiles entre bandes; vectors identificats per `bandSetId` i configuració `spectralBandCount` sense límit fix.

## Errors, cancel·lació i recursos

- Resultats obsolets es descarten per revisió; cap càlcul llarg bloqueja el render thread.
- Fallbacks i dades absents es declaren amb procedència; no s'inventen valors.
- Risc principal: Duplicar ray-march per banda o reutilitzar cache amb un `bandSetId` incompatible.
- Rollback: Conservar configuració d'una banda.

## Tasques

- [ ] Implementar només l'abast d'aquest pas amb contractes i unitats explícites.
- [ ] Afegir instrumentació i procedència necessàries.
- [ ] Integrar cancel·lació/revisions obsoletes quan hi hagi treball asíncron.
- [ ] Executar proves de coherència, unitats i configuració activa, sense benchmarks per determinar el nombre de bandes.
- [ ] Actualitzar inventari, README i evidències només segons estat real.

## Criteri de sortida

B2a verifica la configuració espectral activa, les unitats, els límits i la longitud dels vectors; no executa cap sweep de temps ni benchmark per seleccionar N. El resultat queda reproduïble i no anticipa capacitats posteriors.

## Proves i evidències obligatòries

- [ ] equivalència 1 banda, unitats i longituds de vector.
- [ ] B2a: configuració activa, dimensions i invalidació de cache en canviar `spectralBandCount`; sense benchmark de N.
- [ ] Guardar JSON/CSV/plots o golden data sota `docs/evidencies/pas7.5/` quan s'executi.
- [ ] Executar `tools/validate_docs.py` i regressions afectades abans de completar.

## Fora d'abast

RSR i priors SPD.

## Instrucció per a Codex

compartir geometria i tiles entre bandes; vectors identificats per `bandSetId`. No redissenyar decisions congelades del dossier; si una hipòtesi de benchmark falla, registrar l'evidència i proposar un ADR de substitució.

## Treball pendent

- [ ] Completar totes les tasques, proves i evidències abans de moure aquest document a `completat/`.