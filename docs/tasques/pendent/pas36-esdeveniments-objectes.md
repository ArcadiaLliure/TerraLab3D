# Pas 36 — Esdeveniments propis de planetes i Lluna

> **Estat:** parcial. **Estat funcional:** parcial. **Origen:** planificat. **Abast vigent:** esdeveniments propis de planetes i lluna, integració observable i persistència associada.

## Descripció funcional

La fitxa d'un planeta o de la Lluna mostra els seus propers esdeveniments aplicables —oposició, màxima elongació, fases, perigeu/apogeu— amb icona, instant, valor geomètric i acció per saltar-hi.

## Fonts a consultar

- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d): oracle autoritzat de comportament.

Decisions tancades de referència:
- Els tipus aplicables depenen del cos: planetes exteriors, oposició; interiors, màximes elongacions; Lluna, fases i perigeu/apogeu.
- “Propi” descriu una fita semàntica del cos, encara que el càlcul utilitzi relacions amb Sol/Terra/observador.
- Els serveis reutilitzen mostreig, refinament, versions i cancel·lació del pas 32.
- Cada resultat inclou instant UTC, tipus, cos, valor/angle/distància, observador o centre de referència, precisió i procedència.
- Les fitxes demanen una finestra acotada i carreguen aquests resultats de forma lazy.

## Objectiu

Completar la vertical de «esdeveniments propis de planetes i lluna» de punta a punta, mantenint la separació de responsabilitats, contractes tipats i integració amb el renderer Three.js sense anticipar capacitats posteriors.

## Dependències

**Depèn de:**
- [Pas 32 — Motor general d'efemèrides](pas32-motor-efemerides.md)
- [Pas 33 — Cercador d'objectes i efemèrides](pas33-cercador-objectes-efemerides.md)

**En depenen:**
- [Pas 38 — Homologació final, recuperació i rendiment](pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** - Efemèride: [`spice_adapter.py`](../../../backend/src/terralab3d/infrastructure/adapters/ephemeris/spice_adapter.py), [`astronomical_events.py`](../../../backend/src/terralab3d/application/astronomical_events.py) i [`solar_system/calculations.py`](../../../backend/src/terralab3d/domain/solar_system/calculations.py).
- Model solar: [`solar_system/models.py`](../../../backend/src/terralab3d/domain/solar_system/models.py) i [`solar_system/catalog.py`](../../../backend/src/terralab3d/domain/solar_system/catalog.py).
- Fitxa: [`InspectionModelBuilder.ts`](../../../frontend/src/application/InspectionModelBuilder.ts) i [`CelestialSelectionController.ts`](../../../frontend/src/application/CelestialSelectionController.ts).
- Contractes: [`astronomical_event_contracts.ts`](../../../frontend/src/contracts/astronomical_event_contracts.ts).
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Cos seleccionat → tipus aplicables → consulta acotada → geometria SPICE → detecció/refinament → esdeveniments versionats → model d'inspecció → cards i comanda de temps.

## Errors, cancel·lació i recursos

- Canviar de selecció cancel·la la consulta i no mostra resultats del cos anterior.
- Cos/tipus no aplicable produeix absència tipada; recurs SPICE absent és un error accionable.
- Cache i workers es limiten per cos/finestra i es netegen en canviar versions de kernel.

## Tasques

- [x] SPICE calcula posicions de planetes i Lluna i el pas 32 aporta primitives d'efemèrides.
- [x] La UI disposa d'un model de fitxa/inspecció i del patró “anar a la data”.
- [ ] No hi ha serveis per tipus de cos ni cards d'esdeveniments propis.
- [ ] Definir aplicabilitat, DTOs i convencions geomètriques per cada tipus.
- [ ] Implementar oposicions i màximes elongacions amb bracketing/refinament del pas 32.
- [ ] Implementar fases lunars i perigeu/apogeu amb definicions i centres de referència explícits.
- [ ] Exposar consulta “propers N” cancel·lable, cacheada per cos/interval/versions.
- [ ] Afegir cards lazy a la fitxa amb icona, valor, estat buit/error i “anar a la data”.
- [ ] Validar contra efemèrides externes auditables i documentar toleràncies.

## Criteri de sortida

Cada cos mostra només els esdeveniments que li corresponen, amb valors i instants dins tolerància, i les cards es carreguen/cancel·len sense contaminar la selecció o el temps actual.

## Proves i evidències obligatòries

- [ ] Oposició de Mart, elongacions de Mercuri/Venus, quatre fases lunars i perigeu/apogeu coneguts.
- [ ] Vores de finestra, multiple events, no aplicable, kernel absent i cancel·lació.
- [ ] Toleràncies angulars/temporals contra fonts de referència.
- [ ] Fitxa lazy, canvi ràpid de cos i “anar a la data”.
- [ ] Taula de casos coneguts i toleràncies.
- [ ] Captures de Mart i Lluna amb cards diferents.
- [ ] Vídeo de canvi ràpid de cos i salt temporal.
- [ ] Proves de cache, cancel·lació i recurs absent.

## Fora d'abast

Control d'instruments, notificacions del sistema i nous esdeveniments entre objectes ja coberts pel pas 32.

## Instrucció per a Codex

Amplia el motor del pas 32 amb serveis específics per cos i integra'ls de forma lazy a la fitxa existent. Fixa definicions i centres de referència abans de calcular i reutilitza el patró global d'“anar a la data”.

## Treball pendent

- [ ] Completar totes les tasques i evidències d'aquest pas abans de tancar el criteri de sortida.
