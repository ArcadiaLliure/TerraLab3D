# Pas 7.27 — Skyglow físic — Composició lineal del cel i estats reference/instantaneous

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Completar obligatòriament la ruta selector realista/K → font → transport → radiància → cel. Conservar el lliscant horitzontal, etiqueta superior «Temperatura de color», mínim a l’esquerra, màxim a la dreta, valor actual en K i etiqueta inferior «Exemple: ...», família i font visibles; teclat/ratolí/tacte verificats. Provar que canviar exemple no selecciona tecnologia i que el mode físic i el visual històric no se sumen dues vegades.

## Descripció funcional

Integrar el canal artificial amb la resta del cel sense doble comptatge ni calibratge creuat.

## Fonts a consultar

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [06-contractes-dades.md](../../skyglow/06-contractes-dades.md)

Fonts locals del pla vigent consultades el 2026-10-18; cap asset no es declara validat només per una referència.

## Objectiu

Completar obligatòriament la ruta selector realista/K → font → transport → radiància → cel. Conservar el lliscant horitzontal, etiqueta superior «Temperatura de color», mínim a l’esquerra, màxim a la dreta, valor actual en K i etiqueta inferior «Exemple: ...», família i font visibles; teclat/ratolí/tacte verificats. Provar que canviar exemple no selecciona tecnologia i que el mode físic i el visual històric no se sumen dues vegades.

## Dependències

**Depèn de:**
- [Pas 7.26](pas7.26-three-renderer-debug.md)
- [Pas 7.5.1](../completat/pas7.5.1-black-marble-spectral-simulation.md)

**En depenen:**
- [Pas 7.28](pas7.28-b7-homologacio-skyglow.md)

## Codi existent a reutilitzar

- **Repositori actual:** [SourceModel S/C](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [escenaris i configuració](../../../backend/src/terralab3d/domain/light_pollution/simulation.py), [biblioteca](../../../backend/src/terralab3d/domain/light_pollution/spectral_library.py) i [controls](../../../frontend/src/view/ui/components/SkyglowControls.ts). Reutilitzar els contractes sense duplicar el motor.
- **Projectes de referència autoritzats:** cap runtime extern; els oracles científics independents han de tenir fonts i llicències verificades abans d’incorporar-los.

## Flux tècnic

Configuració versionada + SourceModel S/C + procedència → component del pas → sortida amb unitats, revisió i qualificació pròpies. Completar obligatòriament la ruta selector realista/K → font → transport → radiància → cel. Conservar el lliscant horitzontal, etiqueta superior «Temperatura de color», mínim a l’esquerra, màxim a la dreta, valor actual en K i etiqueta inferior «Exemple: ...», família i font visibles; teclat/ratolí/tacte verificats. Provar que canviar exemple no selecciona tecnologia i que el mode físic i el visual històric no se sumen dues vegades.

## Errors, cancel·lació i recursos

Previst: rebutjar entrades no finites, unitats i revisions incompatibles; cancel·lació cooperativa, latest-wins i descart de resultats antics. Recursos grans persistents fora del JSON de cada frame; alliberament explícit pel propietari. RSR de referència C no es promou a H; incertesa desconeguda no es converteix en sigma.

## Tasques

- [ ] Definir `SkyRadianceComposer` amb canals artificial, natural sense Lluna, lunar i crepuscular.
- [ ] Mantenir `reference` i `instantaneous` amb provenance separada.
- [ ] Fer la suma en radiància lineal abans d’exposició/tone mapping.
- [ ] Permetre que canals astrals encara no físics entrin com a estratègies/versionats sense modificar el canal artificial.
- [ ] Provar linealitat, commutativitat i absència de double count amb Pas 7 històric/7.51+.
- [ ] Completar obligatòriament la ruta selector realista/K → font → transport → radiància → cel. Conservar el lliscant horitzontal, etiqueta superior «Temperatura de color», mínim a l’esquerra, màxim a la dreta, valor actual en K i etiqueta inferior «Exemple: ...», família i font visibles; teclat/ratolí/tacte verificats. Provar que canviar exemple no selecciona tecnologia i que el mode físic i el visual històric no se sumen dues vegades.

## Criteri de sortida

El skyglow artificial conserva identitat i provenance dins la composició; la Lluna/crepuscle no canvien la inferència artificial i `reference` és invariant als components instantanis.

## Proves i evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.27/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.
- [ ] Verificar el nou abast S/C i les modalitats realista/K amb casos independents; H conserva el seu contrast empíric.

**Resultats verificats:** aquest pas encara no s’ha executat; les proves de configuració/font corresponen a 7.5.1.

## Fora d'abast

Homologar H sense observacions; fabricar fonts o radiància; modificar llindars després dels resultats.

## Instrucció per a Codex

No facis servir una lectura SQM total per recalibrar el canal artificial.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

## Treball pendent

- [ ] Executar les tasques i demostrar el criteri de sortida d’aquest pas. La connexió gràfica final de kelvins continua obligatòria fins a 7.27.
