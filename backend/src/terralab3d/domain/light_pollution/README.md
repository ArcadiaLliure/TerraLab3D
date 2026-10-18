# Capacitat `light_pollution` — contaminació lumínica

## 1. Propòsit

Resoldre Bortle, magnitud límit, modes automàtics i efectes sobre el cel i els catàlegs.

El [model DNB de 7.3](dnb_measurement.py) integra radiància espectral TOA al sensor amb una RSR tabulada sense renormalitzar-la; conserva plataforma, producte, guany, data i procedència en el resultat serialitzat. La [User Guide Black Marble C2 §2.2 Eq. (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) documenta la correcció TOA→radiància nocturna ascendent de superfície L3. L'[observació VNP46](vnp46.py) etiqueta aquesta etapa; el [contrast amb VJ146 real](../../../../../docs/evidencies/pas7.3/contrast-granuls-black-marble-c2.md) en confirma capa, unitats i QA. La referència pública RSR i els escenaris C relatius NOAA-20 s’implementen a 7.5.1; incertesa de propagació i homologació H corresponen a 7.16–7.24; cap font urbana de producte està homologada.

El [Pas 7.5](source_model.py) implementa un `SourceModel` **S** immutable per a SPD tabulades, geometries puntuals o rectangles uniformes, escala absoluta definida o paramètrica i perfils angulars axials o separables azimutals. El [contrast CIE i analític](../../../../../docs/evidencies/pas7.5/validacio-source-model-s-v1.md) verifica les integrals i les unitats; no hi ha encara transport SG-REF. El mateix mòdul conserva el gate L3/RSR acreditat per a H, que classifica una base de mesura VNP46 segons QA, dia, unitat i evidència. La [matriu observacional](../../../../../docs/evidencies/pas7.5/estat-inferencia-font-2026.md) manté aquesta branca sense font urbana homologada.

## 2. Pertinença arquitectònica

**Model / Domini científic.** El paquet conté dades pures, invariants, contractes de càlcul i serveis de domini. No conté accés a fitxers, xarxa, threads, UI ni Three.js.

## 3. Entrades i sortides

- **Entrades:** Mode, Bortle, radiància del cel, ubicació i condicions atmosfèriques.
- **Sortides:** Límit de visibilitat i paràmetres de brillantor de cel.

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
| `LightPollutionState` | Entitat | Mode i valor autoritatiu | Esquelet |
| `VisibilityLimit` | DTO | Magnitud límit efectiva | Esquelet |
| `LightPollutionCalculator` | Protocol científic | Conversió i efectes | Esquelet |

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
| `TerraLab/light_pollution/*` | `modes i polítiques` | Lògica i comportament actuals | Regles científiques, invariants, fixtures i semàntica útils | Qt, QPainter, diccionaris sense tipus, threads o I/O que no pertanyin al domini | Aïllar, tipar i caracteritzar abans de traslladar | `backend/src/terralab3d/domain/light_pollution` | `EXTRACT` |
| `TerraLab/terrain/terrain_coordinator.py` | `estimació geogràfica de Bortle` | Lògica i comportament actuals | Regles científiques, invariants, fixtures i semàntica útils | Qt, QPainter, diccionaris sense tipus, threads o I/O que no pertanyin al domini | Aïllar, tipar i caracteritzar abans de traslladar | `backend/src/terralab3d/domain/light_pollution` | `ADAPT` |

Cap fila autoritza copiar un fitxer complet. Primer s’ha de separar ciència, coordinació, I/O i presentació; després s’ha de comparar el resultat amb fixtures de TerraLab.


## Simulació espectral condicionada (7.5.1)

`spectral_library.py` resol colorimetria, interpolació Kelvin i mescles de taules CIE; `simulation.py` defineix configuració, normalitzacions, escenaris C i claus deterministes. La lectura dels assets és d’infraestructura. Fonts S/C comparteixen el contracte de transport; C només admet escala relativa i conserva hipòtesis/procedència. El controlador d’aplicació i la UI configuren fonts; el transport SG-REF comença a 7.6.
