# Pas 24 — Catàleg de recursos i descàrregues persistents

> **Estat:** parcial. **Estat funcional:** parcial. **Origen:** planificat. **Abast vigent:** catàleg de recursos i descàrregues persistents, integració observable i persistència associada.

## Descripció funcional

L'usuari descobreix recursos des d'un catàleg únic, entén mida/llicència/variant, inicia o pausa descàrregues, les reprèn després de reiniciar, les cancel·la o elimina i mai veu un progrés falsament bloquejat.

## Fonts a consultar

- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d): oracle autoritzat de comportament.

Decisions tancades de referència:
- `ResourceDescriptor`, `LayerDescriptor` i `DownloadJob` són conceptes diferents, units per identificadors estables.
- El catàleg declara versions, variants, bundles, mida, checksum, llicència i mode `managed` o `external`.
- Estats mínims del treball: en cua, resolent, descarregant, pausant, pausat, verificant, instal·lant, completat, cancel·lat i error recuperable/terminal.
- Pausa i reanudació utilitzen HTTP Range quan l'origen ho admet; si no, la UI explica que cal reiniciar la transferència.
- La instal·lació és atòmica: temporal → verificació de mida/checksum → `rename` → registre. Un fitxer parcial mai compta com a disponible.
- En arrencar, els treballs interromputs es reconcilien una sola vegada i es presenta una decisió clara; no es creen descàrregues automàtiques.
- Progrés indeterminat, bytes, MB/s i temps estimat tenen semàntica separada.
- El gestor admet **proveïdors autenticats** sense incorporar secrets al catàleg, al `DownloadJob`, als logs ni a la provenance. Els descriptors només poden conservar una referència opaca a la credencial/sessió gestionada fora del recurs.
- Un recurs pot ser **dinàmic**: el catàleg descriu proveïdor, producte/release i selectors (data, tile, AOI o equivalent), i un resolver del proveïdor materialitza l'asset immutable concret abans de transferir-lo. La identitat resolta queda persistida per poder reproduir i auditar la descàrrega.
- El checksum de font és estructurat com a mínim per `algorithm + value` i conserva el seu origen. TerraLab3D calcula a més un SHA-256 local dels bytes instal·lats; el hash local no es presenta com si fos una verificació independent del proveïdor.
- **Black Marble C2 via LAADS/Earthdata és el cas d'acceptació d'aquest flux autenticat i dinàmic** per `VNP46A2.002`, `VJ146A2.002` i `VJ246A2.002`: l'usuari ordinari no ha de conèixer noms de grànul, HDF5 ni URLs d'arxiu. El [perfil multisatèl·lit](../../skyglow/skyglow-v2-profile.json), el [contracte de mesura de 7.3](../completat/pas7.3-dnb-rsr-measurement.md) i l'admissibilitat científica de 7.5 decideixen l'ús físic; el gestor de transferència només obté recursos.

## Objectiu

Completar la vertical de «catàleg de recursos i descàrregues persistents» de punta a punta, mantenint la separació de responsabilitats, contractes tipats i integració amb el renderer Three.js sense anticipar capacitats posteriors.

## Dependències

**Depèn de:**
- [Pas 7.5.1 — contractes d’assets Black Marble/RSR/SPD](../completat/pas7.5.1-black-marble-spectral-simulation.md)
- [Pas 8.6 — Planetes, anells i satèl·lits naturals](../completat/pas8.6.md)
- [Pas 12 — Cerca astronòmica, focus i seguiment](../completat/pas12.md)
- [Pas 7.3 — contracte Black Marble TOA/L3](../completat/pas7.3-dnb-rsr-measurement.md) per al cas d'acceptació VNP46/VJ146/VJ246; el gestor comú no decideix admissibilitat científica.

**En depenen:**
- [Pas 25 — Gestor de capes Cel/Terra](pas25-gestor-capes.md)
- [Pas 26 — Vista de recursos del Sistema Solar](pas26-recursos-sistema-solar.md)
- [Pas 27 — Carta de recursos d'espai profund](pas27-recursos-espai-profund.md)
- [Pas 28 — Descobriment de DEM multiproveïdor](pas28-dem-multiproveidor.md)
- [Pas 29 — Superfície semàntica, TLST i refinament](pas29-superficie-semantica.md)
- [Pas 38 — Homologació final, recuperació i rendiment](pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** - Backend: [`download_manager.py`](../../../backend/src/terralab3d/infrastructure/resources/download_manager.py), [`acquirers.py`](../../../backend/src/terralab3d/infrastructure/resources/acquirers.py), [`installation_repository.py`](../../../backend/src/terralab3d/infrastructure/resources/installation_repository.py) i [`layer_database.py`](../../../backend/src/terralab3d/infrastructure/resources/layer_database.py).
- Domini: [`resources/models.py`](../../../backend/src/terralab3d/domain/resources/models.py) i [`resources/services.py`](../../../backend/src/terralab3d/domain/resources/services.py).
- Frontend: [`ResourceManager.ts`](../../../frontend/src/application/ResourceManager.ts), [`ResourceManagerModal.ts`](../../../frontend/src/view/ui/modals/ResourceManagerModal.ts), [`ResourceBackedLayerRow.ts`](../../../frontend/src/view/ui/components/ResourceBackedLayerRow.ts) i [`resource_manager_contracts.ts`](../../../frontend/src/contracts/resource_manager_contracts.ts).
- Pont: [`ScienceBridge.ts`](../../../frontend/src/bridge/ScienceBridge.ts) i [`bridge_messages.ts`](../../../frontend/src/contracts/bridge_messages.ts).
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Catàleg versionat → selecció de variant/bundle o petició dinàmica → resolució de proveïdor/asset (amb autenticació si cal) → `DownloadJob` persistent amb identitat resolta → adquisidor cancel·lable → temporal reanudable → verificació del checksum de font + SHA-256 local → instal·lació atòmica → registre → delta de disponibilitat cap a la UI.

Per a recursos dinàmics, la resolució i la transferència són fases diferents: una resposta del resolver mai es converteix directament en dada científica. Per a Black Marble, `product∈{VNP46A2,VJ146A2,VJ246A2}`, `collection=002`, dia exacte i tile/AOI resolen un grànul concret. La cadena és `catàleg → producte/dia/AOI → resolució LAADS → autenticació Earthdata → descàrrega persistent → checksum de font + SHA-256 local → instal·lació atòmica → lectura científica específica`. El gestor retorna identitat i path verificat, i conserva les alternatives/fallades sense triar una font com a científicament equivalent. El lector VNP46 del Pas 7.2 només consumeix el fitxer local; l’adaptador J1 queda verificat localment a 7.5.1; J2 requereix proves pròpies.

## Errors, cancel·lació i recursos

- Cancel·lar conserva o elimina el parcial segons una decisió explícita; eliminar no afecta fitxers externs sense confirmació específica.
- Canvis d'ETag, checksum incorrecte o espai insuficient produeixen error accionable i mai promocionen el temporal.
- Reiniciar recupera una cua coherent i no duplica treballs pel mateix recurs/variant.
- Streams, fitxers temporals, tasks i subscripcions es tanquen en tots els camins.
- Credencial absent, caducada o rebutjada és un estat accionable del proveïdor, no un error de dades ni un motiu per degradar silenciosament a una URL alternativa.
- La UI pot demanar configurar/autenticar un proveïdor quan una acció ho requereix, però una credencial mai s'exporta amb manifests, evidències o còpies de projecte.
- Un canvi del grànul/asset resolt, ETag o checksum després de reprendre obliga a revalidar la transferència; no es concatena contingut de dues revisions.

## Tasques

- [ ] Adquirir ordinàriament grànuls Black Marble, RSR per sensor/mode i biblioteques SPD opcionals mitjançant el gestor comú, preservant fonts, llicències, checksums i revisions. Les petites taules CIE obligatòries empaquetades de 7.5.1 segueixen ADR 0005; evitar gestors científics de descàrrega paral·lels.


- [x] Backend i frontend ja modelen recursos, adquisició, instal·lació i progrés bàsic.
- [x] Existeixen modal central, cards de recurs i base de dades de capes.
- [ ] Els treballs no cobreixen encara tot el cicle persistent, reanudable, verificat i recuperable després d'un reinici.
- [ ] Formalitzar esquemes versionats de catàleg, instal·lació i treball, amb migracions i invariants.
- [ ] Persistir cues, temporals, offsets, ETag/Last-Modified, intents i últim error de manera transaccional.
- [ ] Implementar pausa, reanudació, cancel·lació cooperativa, reintents amb backoff i eliminació segura.
- [ ] Verificar mida/checksum i fer instal·lació atòmica; reconciliar temporals i registres després d'un crash.
- [ ] Formalitzar `ChecksumSpec` amb algoritme, valor i origen; conservar el checksum de font quan existeix i calcular sempre un SHA-256 local separat per identitat interna.
- [ ] Formalitzar proveïdors/resolvers d'assets dinàmics perquè selectors estables (producte/release/data/tile/AOI) es resolguin a un asset concret abans de crear o iniciar la transferència.
- [ ] Admetre autenticació de proveïdor mitjançant referències opaques a credencials o sessions gestionades fora dels manifests i jobs; cap secret pot persistir al catàleg, logs o provenance.
- [ ] Integrar LAADS/Earthdata + els tres productes C2 com a casos d'acceptació del mateix flux autenticat: resolució per dia/AOI, descàrrega, verificació, instal·lació i lliurament del path local a l'adaptador de cada producte. Cobrir absència, QA insuficient i model científic no homologat com a estats diferents; l'últim és propietat del consumidor, no un error de descàrrega.
- [ ] Representar variants, bundles, dependències, recursos externs i llicències a la UI.
- [ ] Mostrar estat d'autenticació/requisit de credencial sense exposar secrets; l'ús ordinari de Black Marble no ha d'exigir URLs o fitxers HDF5 manuals. Permetre selecció avançada de plataforma amb provenance i fallback explícit, sense substituir un sensor en silenci.
- [ ] Mostrar progrés determinat o indeterminat, bytes, velocitat i ETA sense confondre transferència amb instal·lació.
- [ ] Unificar tots els punts d'entrada en el mateix gestor i emetre deltes, no snapshots globals continus.

## Criteri de sortida

Qualsevol recurs gestionat passa per un únic cicle persistent i auditable; les transferències es poden recuperar i la disponibilitat només canvia després d'una verificació i instal·lació atòmiques. El mateix cicle cobreix recursos públics, autenticats i resolts dinàmicament sense filtrar secrets ni crear downloaders específics per vertical.

## Proves i evidències obligatòries

- [ ] Servidor amb/sense Range, tall de xarxa, ETag canviat, checksum erroni, cancel·lació i reintent.
- [ ] Reinici durant descàrrega, verificació i instal·lació; reconciliació de temporals orfes.
- [ ] Bundles, variants, dependències, recursos externs i eliminació.
- [ ] Curses de comandes i monotonia de bytes/progrés.
- [ ] Matriu automatitzada de recuperació i cancel·lació.
- [ ] Vídeo de pausa, reinici de l'aplicació i reanudació.
- [ ] Registre de checksum fallit sense recurs disponible.
- [ ] Checksum de font amb almenys dos algoritmes admesos i SHA-256 local independent; demostrar que no es confonen els dos rols.
- [ ] Proveïdor autenticat: credencial absent, vàlida, caducada/rebutjada i reintent després de reautenticar; cap secret apareix en logs, manifests, jobs o provenance.
- [ ] Resolver dinàmic: mateix selector → mateixa identitat d'asset mentre el proveïdor no canvia la revisió; canvi de revisió/checksum → nova identitat verificable.
- [ ] Cas d'acceptació LAADS/Earthdata amb grànuls reals dels tres productes, lliurats com a fitxers locals verificats; el grànul VNP46 ja aportat localment a 7.2 no prova l'adquisició comuna ni els contractes J1/J2.
- [ ] Captures de variants, bundles, llicència, requisit d'autenticació i progrés indeterminat.

## Fora d'abast

Descobriment específic de DEM, UX de capes Cel/Terra i dades base que s'empaqueten amb l'aplicació.

## Instrucció per a Codex

Evoluciona el gestor existent; no en creïs un de paral·lel. Separa recurs, capa i treball, conserva temporals verificables i demostra recuperació després de reinici abans de marcar el pas complet. Els adapters científics (inclòs VNP46 del Pas 7.2) no poden implementar un downloader propi: demanen un recurs al gestor i consumeixen únicament l'asset local verificat.

## Treball pendent

- [ ] Completar totes les tasques i evidències d'aquest pas abans de tancar el criteri de sortida.
