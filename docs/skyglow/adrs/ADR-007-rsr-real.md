# ADR-007 — Utilitzar la RSR real del DNB

- **Estat:** Acceptada — implementació pendent
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Centre/FWHM/rectangle perden la forma real del sensor.

## Decisió

Integrar contra la RSR oficial versionada i checksum.

## Conseqüències

Més fidelitat; introdueix gestió de recurs/llicència.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Test integral contra fixture oficial i provenance.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.