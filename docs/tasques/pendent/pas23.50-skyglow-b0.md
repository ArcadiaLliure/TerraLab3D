# Pas 23.50 — Skyglow físic — benchmark B0 i infraestructura de mesura

> **Estat:** Pendent
> **Dependències:** Pas 7, Pas 22.5 i dossier `docs/skyglow/`

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Crear el harness determinista B0 sense física, amb 900 LOS, segmentació per tiles i Gauss–Kronrod 7/15.

## Descripció funcional

Permet mesurar overhead estructural abans d'introduir Rayleigh, espectre o VIIRS.

## Abast

Harness, fixtures sintètiques, comptadors, JSON/CSV i metadades de hardware/runtime.

## Fora d'abast

Cap canvi visual, cap VIIRS real, cap aerosol físic.

## Fitxers previsibles

nou paquet backend de benchmark skyglow; tests; `docs/evidencies/pas23.50/`.

## Contractes

`BenchmarkRun`, `BenchmarkMetrics`, `BenchmarkScenario`.

## Implementació

Implementar escenaris i GK 7/15 amb integrand trivial; registrar segments/nodes/subdivisions.

## Proves i comprovacions

Determinisme amb seed, recompte 900 LOS, schema JSON/CSV, no NaN.

## Benchmark / rendiment

B0 complet, warm-up 5 i 30 repeticions segons protocol.

## Criteris d'acceptació

- [ ] Resultats reproduïbles i p50/p95/p99 generats; cap decisió de producció inferida.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

JSON raw, CSV per iteració, plots i manifest. Les evidències noves s'han de desar sota `docs/evidencies/pas23.50/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Mesurar el harness en lloc del kernel futur.

## Rollback

Eliminar només el paquet de benchmark nou; cap ruta productiva afectada.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.