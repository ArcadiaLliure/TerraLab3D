# Pas 23.57 — Skyglow físic — adaptador de productes VIIRS/VNL/Black Marble

> **Estat:** Pendent
> **Dependències:** Pas 23.55

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Convertir productes reals a observacions de font amb semàntica i qualitat explícites.

## Descripció funcional

Diferencia DNB SDR, VNL i Black Marble abans del model de font.

## Abast

Almenys un producte actual del projecte i fixtures dels altres.

## Fora d'abast

Gestor de descàrregues complet del Pas 24.

## Fitxers previsibles

adaptador infraestructura light_pollution, ports, fixtures.

## Contractes

`ViirsSourceObservation`, quality/provenance.

## Implementació

Unitats, nodata, masks, CRS, processing level i dates.

## Proves i comprovacions

Raster fixture, unit conversion, nodata, product mismatch.

## Benchmark / rendiment

Throughput ingest/preprocess separat del kernel.

## Criteris d'acceptació

- [ ] Cap raster entra al kernel sense productId/provenance.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

manifest fixture i tests. Les evidències noves s'han de desar sota `docs/evidencies/pas23.57/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Confondre TOA amb emissió de superfície.

## Rollback

Mantenir adapter legacy separat.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.