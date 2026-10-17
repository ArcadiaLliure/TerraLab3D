# Pas 7.7 — Skyglow físic — PropagationKernel geomètric i benchmark B0

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Construir la frontera única de propagació i la instrumentació abans d’afegir scattering.

## Dependències

7.6

## Referències obligatòries

- [02-arquitectura-integracio.md](../../skyglow/02-arquitectura-integracio.md)
- [03-pipeline-python-typescript-threejs.md](../../skyglow/03-pipeline-python-typescript-threejs.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

## Tasques

- [ ] Definir `PropagationKernel` únic per zenit i qualsevol `DirectionSet`.
- [ ] Implementar geometria ECEF/ENU, LOS, segmentació bàsica i Gauss–Kronrod 7/15 amb integrand trivial.
- [ ] Implementar cancel·lació, revisions i comptadors B0 deterministes.
- [ ] Executar warm-up/repeticions B0 i persistir JSON/CSV amb metadades de hardware/runtime.
- [ ] Provar que 90° no entra per cap camí especial.

## Criteri de sortida

B0 és reproduïble i el kernel retorna resultats geomètrics/unitaris sense NaN; zenit és només una direcció del mateix operador.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.7/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No introdueixis encara caches ni aproximacions de fonts. Mesura l’overhead de la ruta directa.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
