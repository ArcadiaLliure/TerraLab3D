# ADR-009 — OpticalField tiled i versionat

- **Estat:** Acceptada — implementació pendent
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

Test que cap dependència requereix segon ray-march.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.