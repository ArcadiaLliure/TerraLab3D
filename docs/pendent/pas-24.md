# Pas 24 --- Identificació i persistència de constel·lacions IAU

> Estat: **pendent** La classificació de les estrelles es calcula una
> sola vegada durant el postprocés de Gaia TAP i es persisteix als
> fitxers `.npy` generats.

## Resultat funcional palpable

TerraLab3D pot conèixer la constel·lació IAU de cada estrella Gaia sense
efectuar cap càlcul de classificació durant l'execució normal.

Durant la descàrrega i preparació del catàleg Gaia, les coordenades
RA/Dec de cada estrella es classifiquen de forma vectoritzada. El
resultat es converteix en un identificador numèric compacte i queda
emmagatzemat als `.npy` juntament amb la resta de dades estel·lars.

La constel·lació queda disponible posteriorment per a cerca avançada,
picking, fitxes informatives, filtratge i, si convé, filtratge visual a
GPU.

## Fonts TerraLab3D a consultar

- `backend/src/terralab3d/domain/constellations/`
- `backend/src/terralab3d/domain/stars/models.py`
- `backend/src/terralab3d/domain/identifiers.py`
- `backend/src/terralab3d/application/ports/`
- `backend/src/terralab3d/application/star_coordinator.py`
- `backend/src/terralab3d/application/search_coordinator.py`
- `backend/src/terralab3d/infrastructure/adapters/star_catalog_adapter.py`
- `backend/src/terralab3d/infrastructure/adapters/gaia_catalog/`
- pipeline actual de descàrrega, postprocés i generació `.npy` de Gaia
    TAP
- Skyfield 1.55 ---
    `skyfield.constellationlib.load_constellation_map()`

## Objectiu

Incorporar una capacitat general de classificació:

`RA / Dec → constel·lació IAU`

La capacitat ha de quedar desacoblada de Gaia mitjançant una abstracció
pròpia de TerraLab3D. Skyfield és la implementació inicial i ha de
quedar confinat a infraestructura.

Per a les estrelles Gaia, la classificació no forma part del runtime:
s'executa una sola vegada com a postprocés del pipeline de
descàrrega/preparació Gaia TAP i el resultat es persisteix als fitxers
`.npy`.

## Arquitectura prevista

``` text
domain/
└── constellations/
    ├── models.py
    ├── calculations.py
    ├── services.py
    └── identification.py

application/
└── ports/
    └── constellations.py

infrastructure/
└── adapters/
    └── constellation/
        ├── __init__.py
        └── skyfield_adapter.py
```

Separar conceptualment:

``` text
Constellations
├── Identification
│   └── RA/Dec → constel·lació IAU
├── Boundaries
│   └── fronteres oficials
└── Figures
    └── línies, nodes i representació gràfica
```

Aquest pas implementa **Identification**.

## Pipeline Gaia

La classificació s'ha d'incorporar al postprocés que transforma les
dades obtingudes de Gaia TAP en els recursos locals utilitzats per
TerraLab3D.

``` text
Gaia TAP
    ↓
descàrrega de dades
    ↓
normalització / validació
    ↓
RA[N] + Dec[N]
    ↓
ConstellationResolverPort
    ↓
SkyfieldConstellationResolver
    ↓
classificació vectoritzada NumPy
    ↓
constellation_id[N]
    ↓
persistència als .npy
    ↓
catàleg Gaia TerraLab3D preparat
```

La classificació es realitza **una sola vegada** per estrella durant la
generació del catàleg local.

En runtime:

``` text
carregar .npy
    ↓
constellation_id ja disponible
    ↓
0 càlcul de classificació
```

## Representació persistent

`constellation_id` ha d'estar alineat exactament amb la resta de camps
de cada lot o tile Gaia.

Conceptualment:

``` text
ra.npy
dec.npy
mag.npy
bp_rp.npy
source_id.npy
constellation_id.npy
```

S'ha d'adaptar aquesta representació al format `.npy` real ja utilitzat
pel pipeline TerraLab3D, sense introduir una estructura paral·lela
innecessària.

Com que existeixen 88 constel·lacions IAU, `constellation_id` es pot
representar com `uint8`.

Cal mantenir una taula canònica i estable de correspondència entre
l'identificador intern i l'abreviatura IAU de tres lletres:

``` text
uint8 ↔ IAU
0     ↔ And
1     ↔ Ant
...
87    ↔ Vul
```

L'ordre concret s'ha de definir una sola vegada, documentar i mantenir
estable entre versions del catàleg.

## Tasques

- [ ] Definir el contracte de domini per a la identificació de
    constel·lacions.
- [ ] Reutilitzar `ConstellationId` com a identificador fort.
- [ ] Definir `ConstellationResolverPort` a aplicació.
- [ ] Fer que el port accepti RA/Dec sense exposar tipus de Skyfield.
- [ ] Implementar resolució vectoritzada per arrays NumPy.
- [ ] Implementar `SkyfieldConstellationResolver` a infraestructura.
- [ ] Utilitzar `skyfield.constellationlib.load_constellation_map()`.
- [ ] Carregar el mapa de constel·lacions una sola vegada durant el
    procés.
- [ ] Evitar bucles Python estrella per estrella.
- [ ] Garantir la conversió correcta de RA/Dec al format requerit per
    Skyfield.
- [ ] Normalitzar els resultats a les 88 abreviatures oficials IAU.
- [ ] Definir una taula canònica estable `uint8 ↔ abreviatura IAU`.
- [ ] Incorporar la classificació al postprocés de Gaia TAP.
- [ ] Executar-la després de disposar de RA/Dec validades i abans
    d'escriure els recursos locals definitius.
- [ ] Generar `constellation_id[N]` alineat amb la resta de columnes
    del catàleg.
- [ ] Persistir `constellation_id` als `.npy` generats pel pipeline
    Gaia.
- [ ] Adaptar el lector del catàleg Gaia perquè carregui
    `constellation_id`.
- [ ] Incorporar `constellation_id` a `StarBatch` o a l'estructura
    persistent equivalent.
- [ ] Garantir compatibilitat/versionat dels catàlegs Gaia generats
    abans d'aquest pas.
- [ ] Evitar qualsevol recalculació de constel·lacions Gaia durant
    l'arrencada normal.
- [ ] Evitar qualsevol recalculació quan es carreguen batches o tiles
    profunds.
- [ ] Evitar qualsevol classificació durant picking, cerca o
    renderitzat.
- [ ] Fer disponible la constel·lació per a la cerca avançada.
- [ ] Fer disponible la constel·lació per a les fitxes i metadades de
    les estrelles.
- [ ] Fer disponible la constel·lació per a picking.
- [ ] Permetre filtratge lògic per constel·lació.
- [ ] Valorar/publicar `constellation_id` a GPU quan el filtratge
    visual massiu per constel·lació ho requereixi.
- [ ] Si s'envia a GPU, mantenir una representació compacta i
    persistent que eviti reconstruccions innecessàries de buffers.
- [ ] Per OpenNGC, reutilitzar i normalitzar la constel·lació ja
    proporcionada pel catàleg quan existeixi.
- [ ] Reservar el resolver dinàmic per a objectes que no disposin
    d'una classificació persistent o la posició dels quals canviï.
- [ ] Mesurar el rendiment del postprocés vectoritzat.
- [ ] Documentar la nova versió/esquema dels recursos Gaia.

## Objectes estàtics i dinàmics

La persistència és la via principal per als objectes catalogals amb
classificació estable.

``` text
Gaia / cel profund
    ↓
classificació offline
    ↓
persistència
```

Els objectes amb posició celeste variable poden requerir una resolució
dinàmica separada:

``` text
Sol / Lluna / planetes / altres objectes mòbils
    ↓
posició RA/Dec del moment
    ↓
ConstellationResolverPort
    ↓
constel·lació actual
```

Aquesta distinció evita aplicar el cost dinàmic als milions d'estrelles
que no el necessiten.

## CPU i GPU

`constellation_id` forma part de les metadades persistents de cada
estrella i ha d'estar disponible en CPU.

Si el filtratge visual de la cerca avançada necessita ocultar o destacar
milions d'estrelles segons constel·lació, el mateix identificador
compacte pot formar part del recurs GPU.

Exemple conceptual:

``` text
Star GPU buffer
├── position
├── magnitude
├── color
├── catalog_index
└── constellation_id
```

La presència a GPU dependrà de les necessitats del pipeline de filtratge
visual. No s'ha de recalcular mai la constel·lació a GPU: només s'hi
publica l'identificador ja persistent.

## Criteri de sortida

El pipeline Gaia TAP calcula de forma vectoritzada la constel·lació IAU
de les estrelles una sola vegada durant el postprocés i persisteix el
resultat als recursos `.npy`.

TerraLab3D pot carregar `constellation_id` directament amb la resta de
dades Gaia i utilitzar-lo en cerca, picking, metadades i filtratge sense
efectuar cap classificació de constel·lacions Gaia en runtime.

Skyfield queda encapsulat darrere d'un port propi i la implementació pot
substituir-se sense modificar el domini ni els consumidors de la
capacitat.

## Evidència obligatòria

- [ ] Proves unitàries de `ConstellationResolverPort`.
- [ ] Proves de `SkyfieldConstellationResolver` amb coordenades
    conegudes.
- [ ] Proves específiques a prop de fronteres entre constel·lacions.
- [ ] Prova vectoritzada sobre un lot Gaia real.
- [ ] Benchmark amb 10.000, 100.000 i 1.000.000 d'estrelles.
- [ ] Verificació que `load_constellation_map()` només es carrega una
    vegada per procés.
- [ ] Verificació de correspondència exacta entre files Gaia i
    `constellation_id`.
- [ ] Verificació del dtype `uint8`.
- [ ] Verificació de persistència i relectura des dels `.npy`.
- [ ] Verificació que el resultat després de relectura és idèntic al
    calculat durant el postprocés.
- [ ] Prova que l'arrencada normal no executa classificació Gaia.
- [ ] Prova que carregar un tile profund ja processat no executa
    classificació.
- [ ] Prova de consulta d'una estrella i obtenció de la seva
    constel·lació persistent.
- [ ] Prova de filtre de cerca per constel·lació.
- [ ] Si s'utilitza GPU, prova de filtratge visual per constel·lació
    sense recalcular ni reconstruir el catàleg.
- [ ] Mesura de frame rate abans i després en camp estel·lar dens.

## Fora d'abast del pas

No es dibuixen les fronteres oficials IAU.

No es modifica la representació gràfica de les figures de les
constel·lacions.

No s'implementa un nou editor de constel·lacions.

No es classifiquen les estrelles Gaia en runtime quan `constellation_id`
ja existeix als recursos persistents.

No es recalcula la constel·lació en picking, cerca, càrrega de tile o
renderitzat.

No es força que `constellation_id` resideixi sempre a GPU; només s'hi
incorpora si el filtratge visual ho justifica.

No es modifica el sistema general de coordenades celestes més enllà de
les conversions necessàries per a la classificació.
