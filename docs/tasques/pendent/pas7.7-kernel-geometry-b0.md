# Pas 7.7 — Skyglow físic — PropagationKernel geomètric i benchmark B0

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** kernel runtime geomètric ECEF/ENU, GK7/15 trivial i benchmark B0; sense dispersió.

## Descripció funcional

Construir la frontera única de propagació i la instrumentació abans d’afegir scattering.

## Objectiu

Disposar d’una ruta directa runtime, independent de la quadratura SG-REF, amb el zenit tractat com qualsevol altra direcció i comptadors reproduïbles.

## Dependències

**Depèn de:**

- [Pas 7.6 — SG-REF verificat offline](../completat/pas7.6-sg-ref-reference-solver.md)

**En depenen:**

- [Pas 7.8 — Camp òptic estàndard](pas7.8-optical-field-standard.md)

## Fonts a consultar

- [02-arquitectura-integracio.md](../../skyglow/02-arquitectura-integracio.md)
- [03-pipeline-python-typescript-threejs.md](../../skyglow/03-pipeline-python-typescript-threejs.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

Fonts locals consultades per normalitzar les dependències el 2026-10-18; implementació d’aquest pas encara no executada.

## Codi existent a reutilitzar

- **Repositori actual:** contractes [SourceModel](../../../backend/src/terralab3d/domain/light_pollution/source_model.py) i [referència SG-REF](../../../backend/src/terralab3d/domain/light_pollution/reference_transport.py). Reutilitzar les entrades i fixtures; no copiar l’integrador ni la projecció plana de referència al runtime ECEF/ENU.
- **Projectes de referència autoritzats:** cap implementació externa incorporada. Verificar fonts/llicències abans d’afegir dependències.

## Flux tècnic

Observador i fonts geodèsics + direccions + revisió → geometria ECEF/ENU i segments → GK7/15 amb integrand trivial → resultat geomètric/unitari i comptadors B0 → JSON/CSV de repeticions. No és encara transport atmosfèric.

## Errors, cancel·lació i recursos

Rebutjar coordenades/direccions no finites i revisions incompatibles. Cancel·lació cooperativa i descart de resultats antics per revisió. Comptadors i propietat dels buffers explícits; cap cache/LUT ni recurs GPU nou. Mesurar recursos segons el protocol B0.

## Tasques

- [ ] Definir `PropagationKernel` únic per zenit i qualsevol `DirectionSet`.
- [ ] Implementar geometria ECEF/ENU, LOS, segmentació bàsica i Gauss–Kronrod 7/15 amb integrand trivial.
- [ ] Implementar cancel·lació, revisions i comptadors B0 deterministes.
- [ ] Executar warm-up/repeticions B0 i persistir JSON/CSV amb metadades de hardware/runtime.
- [ ] Provar que 90° no entra per cap camí especial.

## Criteri de sortida

B0 és reproduïble i el kernel retorna resultats geomètrics/unitaris sense NaN; zenit és només una direcció del mateix operador.

## Proves i evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.7/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

**Resultats verificats:** cap implementació ni prova B0 d’aquest pas. La normalització documental després de 7.6 no n’avança l’estat.

## Fora d'abast

Dispersió, extinció física, OpticalField estàndard, terreny/curvatura, fonts agregades, cache, LUT, gates radiomètrics i renderer.

## Instrucció per a Codex

No introdueixis encara caches ni aproximacions de fonts. Mesura l’overhead de la ruta directa.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

## Treball pendent

- [ ] Executar totes les tasques i demostrar B0; conservar la independència respecte de SG-REF i els seus límits de domini.
