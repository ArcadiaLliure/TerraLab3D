# ADR-009 — OpticalField tiled i versionat

- **Estat:** Acceptada — camp estàndard implementat; composició/transport futurs pendents
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Atmosfera espacial/temporalment variable no cap en un estat global únic.

## Decisió

Representar `OpticalField(x,y,z,t)` en tiles/capes versionats; registrar dependències durant quadratura.

## Conseqüències

Cache selectiva i traçabilitat; més metadades.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Dependències de tile/versió/capa recollides durant la quadratura, sense segon ray-march de dependències. Proves de canvis utilitzats/no utilitzats, origen fix i fronteres semiobertes; columnes contrastades amb oracle independent.

## Estat d'implementació

[7.8](../../tasques/completat/pas7.8-optical-field-standard.md) implementa el camp estàndard sec P/T/n, port/provider, interpolació i dependències per capes. [Fixtures 1/2/8 tiles, regressió B0 i oracle de columnes](../../evidencies/pas7.8/validacio-optical-field.md). Encara no hi ha composició ERA5/CAMS, β espectrals, transport radiomètric ni cache.