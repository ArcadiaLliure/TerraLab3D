# ADR-007 — Utilitzar la RSR real del DNB

- **Estat:** Acceptada — implementació pendent
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

VNP46 és la font operativa, però continua derivant d'una mesura DNB de banda ampla. Aproximar la resposta per centre/FWHM/rectangle o ignorar release/data pot introduir una normalització incompatible.

## Decisió

Integrar contra la RSR oficial versionada, amb checksum/procedència, i resoldre-la de manera compatible amb el release i la data d'adquisició de l'observació.

La vertical usa `measurementOperatorId=BAND_INTEGRATED` i conserva `A = L / ∫S·R dλ`. No es normalitza `R` per la seva integral per defecte.

La unitat exacta de `L` queda pendent de verificació directa contra l'ATBD aplicable.

## Conseqüències

Més fidelitat; introdueix gestió de recurs/llicència.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Test integral contra fixture oficial, resolució release/data i provenance. El test no pot donar per verificada una unitat de l'ATBD encara pendent.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.