# Capacitat `coordinates` — coordenades i transformacions astronòmiques

## 1. Propòsit

Transformar coordenades equatorials, horitzontals, eclíptiques, galàctiques i cartesianes sense projectar a píxels.

## 2. Pertinença arquitectònica

**Model / Domini científic.** El paquet conté dades pures, invariants, contractes de càlcul i serveis de domini. No conté accés a fitxers, xarxa, threads, UI ni Three.js.

## 3. Entrades i sortides

- **Entrades:** Coordenades, observador, instant i convencions de referència.
- **Sortides:** Coordenades transformades, direccions unitàries i matrius astronòmiques.

## 4. Dependències permeses

- `terralab3d.domain.science`, tipus geomètrics i identificadors forts.
- Altres paquets de domini només quan la dependència científica sigui explícita i acíclica.
- Biblioteca estàndard i, en la implementació futura, biblioteques numèriques encapsulades darrere contractes.

## 5. Dependències prohibides

- Qt, QPainter, DOM, navegador, WebEngine, Three.js i WebGL.
- Adaptadors concrets, HTTP, sistema de fitxers, configuració global i executors.
- Components de l’escena, shaders i decisions de presentació.

## 6. Classes i contractes previstos

| Element | Tipus | Responsabilitat | Estat |
|---|---|---|---|
| `CoordinateTransformRequest` | DTO | Petició de transformació | Esquelet |
| `CoordinateTransformResult` | DTO | Resultat i metadades | Esquelet |
| `CelestialTransformCalculator` | Protocol científic | Transformacions entre marcs | Esquelet |

El paquet separa `models.py` (tipus i invariants), `calculations.py` (algoritmes científics purs) i `services.py` (composició de regles de domini).

## 7. TODO

- [ ] Definir unitats, dominis, convencions, època de referència i toleràncies de cada valor públic.
- [ ] Caracteritzar numèricament el comportament equivalent de TerraLab amb casos reproduïbles.
- [ ] Implementar els càlculs purs sense I/O, estat global ni dependències gràfiques.
- [ ] Afegir proves de propietats, casos límit i regressió numèrica.
- [ ] Definir quins resultats són estàtics, ocasionals, per tick o per frame.
- [ ] Connectar el servei de domini amb un cas d’ús d’aplicació tipat.
- [ ] Definir els recursos o deltes mínims que l’aplicació haurà de publicar.
- [ ] Validar que moure la càmera no torna a executar aquest paquet excepte quan sigui científicament necessari.

## 8. Migració des de TerraLab

| Origen a TerraLab | Símbol actual | Responsabilitat actual | Part reutilitzable | Part que no s’ha de copiar | Transformació necessària | Destí a TerraLab3D | Estratègia |
|---|---|---|---|---|---|---|---|
| `TerraLab/scene/projection.py` | `RA/Dec a Alt/Az i temps sideral` | Lògica i comportament actuals | Regles científiques, invariants, fixtures i semàntica útils | Qt, QPainter, diccionaris sense tipus, threads o I/O que no pertanyin al domini | Aïllar, tipar i caracteritzar abans de traslladar | `backend/src/terralab3d/domain/coordinates` | `EXTRACT` |
| `TerraLab/widgets/spherical_math.py` | `distàncies, arcs i interpolació esfèrica` | Lògica i comportament actuals | Regles científiques, invariants, fixtures i semàntica útils | Qt, QPainter, diccionaris sense tipus, threads o I/O que no pertanyin al domini | Aïllar, tipar i caracteritzar abans de traslladar | `backend/src/terralab3d/domain/coordinates` | `EXTRACT` |

Cap fila autoritza copiar un fitxer complet. Primer s’ha de separar ciència, coordinació, I/O i presentació; després s’ha de comparar el resultat amb fixtures de TerraLab.
