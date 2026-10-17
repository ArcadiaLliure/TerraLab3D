# Pas 7.19 — Skyglow físic — Compressió de PhaseFunction i benchmark B3

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Aproximar la fase només contra la representació de referència ja validada.

## Dependències

7.18

## Referències obligatòries

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

## Tasques

- [ ] Implementar representació Legendre o equivalent com a backend de `PhaseFunction`.
- [ ] Comparar ordres/candidats contra taula Mie/mesurada o fase d’alta resolució, sobretot forward scattering.
- [ ] Executar B3 amb mateixa geometria/nodes per a tots els candidats.
- [ ] Seleccionar la configuració que compleixi l’error preregistrat; rendiment només desempata configuracions vàlides.
- [ ] Conservar fallback de referència per debug/oracle.

## Criteri de sortida

La fase accelerada té domini i error explícits i compleix V1; si cap candidat ho fa, el runtime conserva la fase de referència.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.19/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No declareu “ordre òptim” només per temps. Primer ha de passar l’error angular/radiomètric.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
