# Pas 23.58 — Skyglow físic — EmissionRegion i watershed radiomètric

> **Estat:** Pendent
> **Dependències:** Pas 23.57

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Segmentar fonts per estructura radiomètrica, no per municipis.

## Descripció funcional

Implementa log-radiance, denoise, threshold, maxima/prominence, watershed i merge.

## Abast

Segmentació determinista i geometria de regió.

## Fora d'abast

Quadtree intern.

## Fitxers previsibles

source segmentation, tests, fixtures.

## Contractes

`EmissionRegion`.

## Implementació

Paràmetres versionats; conservar radiància total i moments.

## Proves i comprovacions

Dues ciutats unides per pont feble, font allargada, soroll, outliers.

## Benchmark / rendiment

Cost de preprocessament per tile/raster.

## Criteris d'acceptació

- [ ] Regions estables i conservació radiomètrica dins tolerància.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

rasters sintètics + masks/plots. Les evidències noves s'han de desar sota `docs/evidencies/pas23.58/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Sobre/infra-segmentació.

## Rollback

Paràmetres anteriors versionats.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.