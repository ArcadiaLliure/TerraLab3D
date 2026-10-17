# Pas 7.6 — Skyglow físic — SG-REF: oracle independent de transport i integració d’àrea

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Crear una veritat numèrica offline més estricta que el runtime i independent de les seves aproximacions.

## Dependències

7.5

## Referències obligatòries

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [04-justificacio-cientifica.md](../../skyglow/04-justificacio-cientifica.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)

## Tasques

- [ ] Implementar `SG-REF` amb toleràncies estrictes, convergència demostrada i integració directa d’àrea/raster de fonts.
- [ ] Evitar compartir amb el runtime codi d’aproximació que pugui produir errors correlacionats; compartir només contractes/constants autoritatives quan sigui segur.
- [ ] Afegir fases de referència d’alta resolució i ruta espectral fina per fixtures.
- [ ] Quantificar offline el biaix single-scattering (`F5`) en el domini v1 amb una referència més rica o oracle extern quan sigui necessari.
- [ ] Crear fixtures sintètiques analítiques i escenaris reproduïbles que seran consumits pels gates posteriors.

## Criteri de sortida

`S1` és executable: SG-REF demostra convergència i pot comparar radiància espectral per direcció i fonts extenses sense quadtree, cache ni LUT de runtime.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.6/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

L’oracle no és una versió “més lenta” del mateix codi aproximat. Si comparteixes una aproximació crítica, documenta per què no invalida la independència.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
