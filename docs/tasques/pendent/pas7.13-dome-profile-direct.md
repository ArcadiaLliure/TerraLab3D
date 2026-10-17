# Pas 7.13 — Skyglow físic — Camp angular i DomeProfile sobre ruta directa

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Estendre el mateix operador homologat del zenit a direccions arbitràries sense acceleracions de fonts.

## Dependències

7.12

## Referències obligatòries

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [03-pipeline-python-typescript-threejs.md](../../skyglow/03-pipeline-python-typescript-threejs.md)

## Tasques

- [ ] Avaluar el kernel directe a les mostres angulars canòniques i a una malla d’oracle més densa.
- [ ] Construir `DomeProfile` i PCHIP sobre `log(B+ε)` amb tests Python/TypeScript compartibles.
- [ ] Verificar wrap d’azimut, positivitat i invariant del zenit.
- [ ] Comparar reconstrucció angular contra SG-REF/all-sky densa.
- [ ] Mesurar error de compressió direccional separat de l’error del kernel.

## Criteri de sortida

`DomeProfile` reprodueix zenit i camp angular directe dins el pressupost V1; la compressió angular té error quantificat independent.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.13/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

Encara no facis watershed/quadtree. El baseline angular ha de néixer de fonts directes.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
