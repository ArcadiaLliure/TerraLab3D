# Pas 23.66 — Skyglow físic — terreny, horitzó i curvatura al kernel

> **Estat:** Pendent
> **Dependències:** Pas 23.59 i Pas 23.51

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Integrar DEM real i curvatura amb visibilitat binària per raig.

## Descripció funcional

Trunca observer→sky i oculta source→P sense transparència de muntanya.

## Abast

Reutilitzar geodèsia/DEM actual, elevacions font/observer, partial region visibility.

## Fora d'abast

Refracció atmosfèrica.

## Fitxers previsibles

terrain/horizon integration, tests.

## Contractes

`TerrainVisibility`/revision.

## Implementació

Mateixa convenció WGS84/ECEF/topocèntrica que projecte.

## Proves i comprovacions

muntanya sintètica, font parcial, Earth curvature far source.

## Benchmark / rendiment

cost visibility per patch/node.

## Criteris d'acceptació

- [ ] Flip visible↔occluded determinista.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

debug plots i tests. Les evidències noves s'han de desar sota `docs/evidencies/pas23.66/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Cost DEM source→P.

## Rollback

Acceleració conservadora; mai smoothing d'oclusió.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.