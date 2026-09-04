# Capacitat `eclipses` — eclipsis i ocultacions

## 1. Propòsit

Calcular geometria de contacte, magnitud, obscuriment, fases i visibilitat local d’eclipsis i ocultacions.

## 2. Pertinença arquitectònica

**Model / Domini científic.** El paquet conté dades pures, invariants, contractes de càlcul i serveis de domini. No conté accés a fitxers, xarxa, threads, UI ni Three.js.

## 3. Entrades i sortides

- **Entrades:** Estats aparents del Sol, Lluna i observador al llarg del temps.
- **Sortides:** Esdeveniments, contactes i estat instantani d’eclipsi.

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
| `AstronomicalEventSnapshot` | DTO | Estat solar/lunar instantani coherent | Implementat |
| `AstronomicalEventSearchResult` | DTO | Contactes i màxim refinats | Implementat |
| `SolarEclipseState` | Valor | Classificació local, magnitud i obscuració | Implementat |
| `LunarEclipseState` | Valor | Penombra/umbra terrestre i magnituds | Implementat |
| `AstronomicalEventCalculator` | Servei pur | Composició renderer-neutral | Implementat |

El paquet separa `models.py` (tipus i invariants), `calculations.py` (algoritmes científics purs) i `services.py` (composició de regles de domini).

## 7. Estat

La capacitat està implementada al Pas 9. Les unitats públiques són graus,
quilòmetres i UTC aware. La classificació no té banda tolerant; les toleràncies
de `0.25 s`/`1e-8°` són exclusives dels solvers numèrics. La càmera no és cap
entrada científica. Vegeu `docs/completat/pas9.md`.

## 8. Migració des de TerraLab

| Origen a TerraLab | Símbol actual | Responsabilitat actual | Part reutilitzable | Part que no s’ha de copiar | Transformació necessària | Destí a TerraLab3D | Estratègia |
|---|---|---|---|---|---|---|---|
| `TerraLab/astro/engine.py; lògica d’eclipsis del renderer` | `càlculs i presentació barrejats` | Lògica i comportament actuals | Regles científiques, invariants, fixtures i semàntica útils | Qt, QPainter, diccionaris sense tipus, threads o I/O que no pertanyin al domini | Aïllar, tipar i caracteritzar abans de traslladar | `backend/src/terralab3d/domain/eclipses` | `EXTRACT` |

Cap fila autoritza copiar un fitxer complet. Primer s’ha de separar ciència, coordinació, I/O i presentació; després s’ha de comparar el resultat amb fixtures de TerraLab.
