# Capacitat `atmosphere` — atmosfera i extinció

## 1. Propòsit

Calcular extinció, dispersió, transparència, terbolesa, boira i atenuació atmosfèrica.

## 2. Pertinença arquitectònica

**Model / Domini científic.** El paquet conté dades pures, invariants, contractes de càlcul i serveis de domini. No conté accés a fitxers, xarxa, threads, UI ni Three.js.

## 3. Entrades i sortides

- **Entrades:** Pressió, temperatura, humitat, aerosols, altitud i trajecte òptic.
- **Sortides:** Paràmetres atmosfèrics i coeficients de visibilitat.

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
| `AtmosphereParameters` | DTO | Estat físic de l’atmosfera | Esquelet |
| `AtmosphericExtinctionCalculator` | Protocol científic | Extinció per altura i longitud d’ona | Esquelet |
| `AtmosphereModel` | Servei | Resolució de paràmetres de cel | Esquelet |

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
| `TerraLab/weather/system.py; TerraLab/render/sky_renderer.py` | `regles atmosfèriques barrejades amb pintura` | Lògica i comportament actuals | Regles científiques, invariants, fixtures i semàntica útils | Qt, QPainter, diccionaris sense tipus, threads o I/O que no pertanyin al domini | Aïllar, tipar i caracteritzar abans de traslladar | `backend/src/terralab3d/domain/atmosphere` | `EXTRACT` |

Cap fila autoritza copiar un fitxer complet. Primer s’ha de separar ciència, coordinació, I/O i presentació; després s’ha de comparar el resultat amb fixtures de TerraLab.
