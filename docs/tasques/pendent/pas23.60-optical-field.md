# Pas 23.60 — Skyglow físic — OpticalField tiled i dependències

> **Estat:** Pendent
> **Dependències:** Pas 23.54

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Crear camp òptic 3D+temps versionat i registrar tiles durant quadratura.

## Descripció funcional

Base per atmosfera variable i cache selectiva.

## Abast

Tiles/capes, versions, lookup, dependency set.

## Fora d'abast

Providers reals.

## Fitxers previsibles

domain/atmosphere i infraestructura cache.

## Contractes

`OpticalState`, `OpticalTile`, `OpticalTileBand`.

## Implementació

Segmentar LOS a límits de tile; cap segon ray-march.

## Proves i comprovacions

Travessa múltiples tiles, versions, dependency exactness.

## Benchmark / rendiment

B0/B1 amb 1/2/8 tiles.

## Criteris d'acceptació

- [ ] Dependències reproduïbles i cost mesurat.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

trace de tiles/nodes. Les evidències noves s'han de desar sota `docs/evidencies/pas23.60/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Granularitat massa fina.

## Rollback

Tiles més grans sense canviar API.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.