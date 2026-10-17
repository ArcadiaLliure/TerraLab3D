# Pas 7.18 — Skyglow físic — Watershed, EmissionRegion i quadtree com acceleració B5

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Comprimir fonts només després de disposar d’una integració directa d’àrea validada.

## Dependències

7.17

## Referències obligatòries

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

## Tasques

- [ ] Implementar watershed radiomètric sobre sortida admissible del SourceModel, no sobre VNP46 cru.
- [ ] Construir `EmissionRegion` i quadtree intern sense travessar regions.
- [ ] Definir error de patch amb cota física i casos d’oclusió parcial.
- [ ] Comparar cada aproximació contra la integració directa d’àrea de SG-REF/runtime baseline.
- [ ] Executar B5 `ε_patch` vs patches/error i activar només configuracions que compleixin V1.
- [ ] Preregistrar qualsevol pressupost nou de compressió abans de seleccionar el candidat B5, amb cota d'error i origen justificats.

## Criteri de sortida

La ruta comprimida és una acceleració demostrablement equivalent dins pressupost al baseline directe; punt vs àrea queda validat en camp proper.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.18/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No utilitzis la mateixa fórmula aproximada com a únic oracle. Si no hi ha guany segur, conserva la ruta directa.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
