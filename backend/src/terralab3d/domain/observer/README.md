# Capacitat `observer` — ubicació de l’observador

## 1. Propòsit

Modelar la posició geodèsica, l’alçada del terreny, l’alçada addicional i el perfil topocèntric de l’observador.

## 2. Pertinença arquitectònica

**Model / Domini científic.** El paquet conté dades pures, invariants, contractes de càlcul i serveis de domini. No conté accés a fitxers, xarxa, threads, UI ni Three.js.

## 3. Entrades i sortides

- **Entrades:** Latitud, longitud, elevació, desplaçament vertical i datum.
- **Sortides:** Perfil d’observador validat i paràmetres topocèntrics.

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
| `GeoLocation` | Entitat | Posició geodèsica immutable | Esquelet |
| `ObserverProfile` | Agregat | Posició efectiva i alçada de l’observador | Esquelet |
| `ObserverGeodesyCalculator` | Protocol científic | Conversió geodèsica i topocèntrica | Esquelet |

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
| `TerraLab/ui/widget_controls_builder.py` | `controls de latitud, longitud i alçada addicional` | Lògica i comportament actuals | Regles científiques, invariants, fixtures i semàntica útils | Qt, QPainter, diccionaris sense tipus, threads o I/O que no pertanyin al domini | Aïllar, tipar i caracteritzar abans de traslladar | `backend/src/terralab3d/domain/observer` | `EXTRACT` |
| `TerraLab/terrain/terrain_coordinator.py` | `consulta d’elevació nua` | Lògica i comportament actuals | Regles científiques, invariants, fixtures i semàntica útils | Qt, QPainter, diccionaris sense tipus, threads o I/O que no pertanyin al domini | Aïllar, tipar i caracteritzar abans de traslladar | `backend/src/terralab3d/domain/observer` | `ADAPT` |

Cap fila autoritza copiar un fitxer complet. Primer s’ha de separar ciència, coordinació, I/O i presentació; després s’ha de comparar el resultat amb fixtures de TerraLab.
