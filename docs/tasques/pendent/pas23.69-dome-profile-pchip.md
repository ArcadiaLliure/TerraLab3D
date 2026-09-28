# Pas 23.69 — Skyglow físic — DomeProfile, mostres angulars i PCHIP

> **Estat:** Pendent
> **Dependències:** Pas 23.51, Pas 23.59 i Pas 23.67

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Comprimir el camp per font a 9 elevacions i reconstruir-lo en log-radiància.

## Descripció funcional

Produeix cúpules direccionals del mateix kernel.

## Abast

0,5/2/5/10/20/30/45/60/90°, PCHIP, zenit, widths.

## Fora d'abast

Renderer final.

## Fitxers previsibles

dome compressor Python/TS golden implementation.

## Contractes

`DomeProfile`.

## Implementació

Suma només després de tornar a radiància lineal.

## Proves i comprovacions

Zenit=90°, positivity, no overshoot, wrap azimuth.

## Benchmark / rendiment

Comparació all-sky, prova mostra 1°.

## Criteris d'acceptació

- [ ] Mètriques de compressió publicades.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

all-sky vs compressed plots. Les evidències noves s'han de desar sota `docs/evidencies/pas23.69/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Error 0–2°.

## Rollback

Afegir mostra 1° o més mostres, mateixa API.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.