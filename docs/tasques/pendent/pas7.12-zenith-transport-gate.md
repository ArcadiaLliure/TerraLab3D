# Pas 7.12 — Skyglow físic — Gate zenital de transport radiomètric

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Validar el transport complet abans de cúpules, compressions o caches.

## Dependències

7.11

## Referències obligatòries

- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)

## Tasques

- [ ] Executar fixtures zenitals sintètiques amb SourceModel conegut contra SG-REF.
- [ ] Executar almenys una fixture VNP46→SourceModel amb atmosfera estàndard i DEM reproduïble.
- [ ] Auditar cadena d’unitats, convergència, error numèric, memòria, nodes i dependències.
- [ ] Separar explícitament l’error de transport de la incertesa del SourceModel.
- [ ] Bloquejar qualsevol pas posterior si necessita un factor de calibratge opac o una ruta especial a 90°.

## Criteri de sortida

El mateix `PropagationKernel` supera el perfil V1 al zenit contra SG-REF sense calibratge arbitrari. El PASS valida transport donat un SourceModel, no la inferència d’emissió.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.12/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

Aquest és el primer gate dur de física runtime. Si falla, corregeix 7.7–7.11; no compensis el resultat en 7.13 o en el renderer.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
