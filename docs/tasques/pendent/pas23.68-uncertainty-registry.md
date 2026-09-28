# Pas 23.68 — Skyglow físic — UncertaintyModelRegistry i propagació

> **Estat:** Pendent
> **Dependències:** Pas 23.56, Pas 23.65 i Pas 23.67

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Separar PredictionUncertainty de CacheValidityUncertainty i modelar correlacions.

## Descripció funcional

Evita barrejar errors epistèmics, sistemàtics i canvi temporal.

## Abast

registry, Jacobians atmosfèrics, SPD ensemble, grups de correlació.

## Fora d'abast

Matriu densa runtime.

## Fitxers previsibles

uncertainty domain/application, tests.

## Contractes

`PredictionUncertainty`, `CacheValidityUncertainty`, `UncertaintyModel`.

## Implementació

`σ_B²=JΣJᵀ` en grups; bounds conservadors per cache.

## Proves i comprovacions

Biaix sistemàtic constant no força miss; correlació ρ=1 vs 0.

## Benchmark / rendiment

uncertainty overhead per B7.

## Criteris d'acceptació

- [ ] Cap sigma inventat per etiqueta provider.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

registry sample + propagation tests. Les evidències noves s'han de desar sota `docs/evidencies/pas23.68/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Falsa precisió.

## Rollback

Intervals conservadors i components separats.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.