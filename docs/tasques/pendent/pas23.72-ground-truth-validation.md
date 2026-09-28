# Pas 23.72 — Skyglow físic — validació TESS/SQM/all-sky

> **Estat:** Pendent
> **Dependències:** Pas 23.69, Pas 23.65 i Pas 23.68

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Comparar prediccions amb mesures reals sense contaminar calibratge i validació.

## Descripció funcional

Simula resposta espectral/FOV de cada instrument i aplica leave-one-site-out.

## Abast

TESS-W, SQM i all-sky disponible; uncertainty budget.

## Fora d'abast

No reajustar el model sobre el conjunt de test.

## Fitxers previsibles

validation scripts, manifests i reports.

## Contractes

`GroundTruthObservation` intern.

## Implementació

Join temporal/geogràfic traçable; filtres de lluna/núvol segons campanya.

## Proves i comprovacions

Data leakage checks i sensor response golden.

## Benchmark / rendiment

No és benchmark runtime; report científic.

## Criteris d'acceptació

- [ ] Errors i intervals per estrat publicats.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

dataset manifest, plots i report. Les evidències noves s'han de desar sota `docs/evidencies/pas23.72/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Ground truth heterogeni.

## Rollback

Mantenir campanya com exploratòria, no calibrar producció.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.