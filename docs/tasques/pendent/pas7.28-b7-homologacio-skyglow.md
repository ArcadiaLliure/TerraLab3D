# Pas 7.28 — Skyglow físic — B7 FULL, SLO i homologació del skyglow artificial

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Tancar la vertical només després que ciència, rendiment i integració hagin passat gates independents.

## Dependències

7.1–7.27

## Referències obligatòries

- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)
- [16-auditoria.md](../../skyglow/16-auditoria.md)

## Tasques

- [ ] Executar B7 amb AD OFF/ON, uncertainty OFF/ON, cold/warm/movement/prefetch/teleport/tile-change/occlusion-flip i backend 7.22 si existeix.
- [ ] Auditar DATA-VNP46 històric i DATA-MULTISAT, DNB-TOA-L3, F1, F5, F7, V1, V3, S1, DNB-2017 i LOW-RAD **per cada plataforma/producte/release/període declarat**, sense exigir homologació de sensors fora de l'abast publicat.
- [ ] Verificar la procedència, versió i congelació prèvia de tots els criteris PASS/FAIL aplicables; consumir-los sense crear-ne ni modificar-ne cap a 7.28.
- [ ] Reexecutar gate zenital, regressions all-sky, projeccions i validació empírica congelada.
- [ ] Verificar `kernelIntegralsPerRenderFrame=0`, stutter i memòria segons els SLO de producte aprovats, i lifecycle.
- [ ] Decidir shadow/default i retirar només els fallbacks que l’evidència autoritza; actualitzar inventari, README i evidències finals.

## Criteri de sortida

La vertical queda `completat` només si no hi ha decisions bloquejants ocultes, tots els gates preregistrats passen i el domini científic homologat identifica plataforma/producte/release/període/QA. Les altres fonts resten pendents explícitament; 7.28 no crea ni modifica criteris. En cas contrari roman parcial/bloquejada amb fallback legacy.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.28/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

Consumeix només criteris ja congelats; no creïs ni modifiquis llindars a 7.28 o després de veure B7. No homologuis una acceleració perquè sigui ràpida ni una font perquè runtime i SG-REF coincideixin.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
