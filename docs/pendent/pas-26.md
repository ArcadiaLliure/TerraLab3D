# Pas 25 --- Cerca avançada d'objectes astronòmics

> Estat: **pendent** Implementa una cerca avançada no modal integrada
> amb el cel, amb filtratge en viu, resultats persistents i capacitat
> d'aïllar visualment els objectes que compleixen els criteris.

## Resultat funcional palpable

L'usuari pot obrir una finestra flotant de cerca avançada des de la
cerca ràpida, combinar criteris astronòmics, instrumentals i
d'observabilitat, veure els resultats actualitzar-se en viu i
inspeccionar-los sense perdre la interacció amb el cel.

Els resultats es mostren en targetes amb les dades necessàries per
decidir què observar, incloent magnitud, constel·lació, sortida/posta,
altitud i una representació compacta de l'evolució de l'altitud durant
l'interval temporal seleccionat.

L'usuari pot mantenir la finestra oberta mentre explora successivament
els resultats i pot activar un mode que oculta del cel els objectes que
no compleixen els filtres.

## Fonts TerraLab3D a consultar

- `backend/src/terralab3d/application/search_coordinator.py`
- `backend/src/terralab3d/application/star_coordinator.py`
- `backend/src/terralab3d/application/ports/`
- `backend/src/terralab3d/domain/stars/`
- `backend/src/terralab3d/domain/constellations/`
- `backend/src/terralab3d/domain/identifiers.py`
- `backend/src/terralab3d/infrastructure/adapters/star_catalog_adapter.py`
- `backend/src/terralab3d/infrastructure/adapters/ngc_catalog/`
- frontend actual de cerca ràpida
- frontend actual de picking, selecció i fitxes d'objecte
- pipeline de buffers persistents d'estrelles
- Pas 24 --- Identificació i persistència de constel·lacions IAU

## Objectiu

Construir una vertical funcional completa de cerca avançada que permeti
consultar de manera homogènia els diferents tipus d'objectes astronòmics
de TerraLab3D sense convertir la interfície en un formulari modal ni
interrompre l'exploració del cel.

La cerca ha de separar:

``` text
criteris de cerca
        ↓
motor de filtratge
        ↓
resultats
        ↓
presentació
        ↓
interacció amb el cel
```

La UI no ha de contenir lògica científica ni accedir directament als
catàlegs.

Els filtres s'han d'aplicar en viu. No hi ha botó «Aplicar filtres».

## Accés des de la cerca ràpida

La cerca avançada s'integra amb el cercador ràpid existent.

Abans que l'usuari escrigui:

``` text
┌──────────────────────────────┐
│ Cerca...                     │
├──────────────────────────────┤
│ Cerca avançada               │
└──────────────────────────────┘
```

Quan ja hi ha text i resultats, l'accés a la cerca avançada apareix al
final del desplegable:

``` text
┌──────────────────────────────┐
│ M42                          │
├──────────────────────────────┤
│ M42 — Nebulosa d'Orió        │
│ ...                          │
├──────────────────────────────┤
│ Cerca avançada               │
└──────────────────────────────┘
```

L'acció obre la finestra avançada sense substituir ni bloquejar la vista
del cel.

## Finestra de cerca avançada

La cerca avançada és una **finestra flotant, no modal i arrossegable**.

Ha de poder romandre oberta mentre l'usuari:

- mou la càmera;
- observa el cel;
- selecciona objectes;
- centra resultats;
- prova diferents objectes;
- modifica filtres.

No s'ha de tancar ni minimitzar automàticament quan l'usuari interactua
amb un resultat.

La barra superior conté, com a mínim:

``` text
┌──────────────────────────────────────────┐
│ Cerca avançada                       ×   │
└──────────────────────────────────────────┘
```

La barra de títol actua com a zona d'arrossegament.

## Distribució general

La superfície principal de la finestra està dedicada als resultats.

Els filtres no han d'ocupar permanentment una part important d'aquesta
superfície. S'accedeix a ells mitjançant una icona de filtre i es
despleguen en un corredor/panell lateral cap a l'esquerra.

``` text
        FILTRES                 RESULTATS
┌───────────────────┐   ┌───────────────────────────┐
│ Tipus             │   │ Cerca avançada         × │
│ Magnitud          │   ├───────────────────────────┤
│ Constel·lació     │   │ Targeta resultat         │
│ Altitud           │   │ Targeta resultat         │
│ Temps             │   │ Targeta resultat         │
│ Mida / FOV        │   │ ...                       │
│ Més filtres       │   │                           │
└───────────────────┘   ├───────────────────────────┤
                        │ ☐ Mostrar només resultats │
                        └───────────────────────────┘
```

El panell de filtres es pot tornar a plegar sense ocultar ni modificar
la zona de resultats.

L'àrea de resultats disposa de scroll independent.

El control inferior de filtratge visual queda fix i no desapareix quan
es fa scroll.

## Comportament dels filtres

Els filtres s'apliquen **en viu**.

``` text
usuari modifica filtre
        ↓
estat de cerca
        ↓
consulta/filtratge
        ↓
nous resultats
        ↓
actualització de targetes
        ↓
actualització del cel si l'aïllament és actiu
```

No s'implementa un botó «Aplicar».

Es pot incorporar una acció «Netejar filtres» per tornar a l'estat
inicial.

L'estat dels filtres ha de mantenir una disposició espacial estable:
activar un tipus d'objecte no ha de provocar que els controls principals
canviïn contínuament de lloc.

## Tipus d'objecte

La cerca avançada ha de poder treballar sobre les grans famílies
d'objectes suportades per TerraLab3D, com a mínim:

``` text
Estrelles
Cel profund
Sistema Solar
```

El model ha de permetre seleccionar més d'un tipus quan la consulta
sigui compatible.

Els filtres específics d'un catàleg o família no s'han de barrejar amb
els filtres comuns.

La semàntica exacta de l'estat «cap tipus seleccionat» i «tots els tipus
seleccionats» s'ha de definir explícitament durant la implementació per
evitar comportaments implícits o contradictoris.

## Filtres comuns

Els filtres comuns han de poder aplicar-se sempre que el tipus d'objecte
disposi de la propietat corresponent.

Com a mínim:

- [ ] Tipus d'objecte.
- [ ] Constel·lació.
- [ ] Magnitud/brillantor quan sigui aplicable.
- [ ] Altitud mínima.
- [ ] Interval temporal d'observació.
- [ ] Mida angular.
- [ ] Compatibilitat amb camp de visió/FOV quan sigui aplicable.
- [ ] Criteris d'observabilitat disponibles.

La constel·lació utilitza la infraestructura definida al Pas 24.

Per Gaia, el filtre treballa sobre el `constellation_id` ja persistent i
no recalcula la constel·lació.

## Interval temporal

La cerca ha de permetre limitar els resultats segons un interval
temporal.

El filtre temporal és un **rang**, no únicament una hora concreta.

Ha d'existir una acció ràpida:

``` text
Ara
```

que permeti portar el rang o l'estat temporal al moment actual segons el
comportament definit per la UI.

La cerca temporal alimenta els càlculs d'altitud, sortida/posta i
qualitat d'observació.

## Altitud mínima

L'usuari pot especificar una altitud mínima acceptable.

Aquest criteri és especialment important per planificació visual i
astrofotogràfica.

La consulta ha de poder determinar si l'objecte supera l'altitud
requerida dins de l'interval temporal seleccionat.

No s'ha de limitar necessàriament a comprovar l'altitud en l'instant
inicial.

## Mida angular i FOV

La cerca avançada reutilitza les capacitats existents o previstes de
mida angular i camp de visió.

Ha de permetre trobar objectes compatibles amb el camp
angular/instrumental seleccionat sense duplicar configuracions de
sensor, focal o FOV que pertanyin al sistema instrumental.

La cerca consumeix aquesta informació; no crea un segon model
d'instrument.

## Filtres específics de catàleg

L'acció:

``` text
Més filtres
```

desplega verticalment criteris més específics.

Aquests filtres s'han de construir a partir de propietats reals
disponibles als catàlegs.

Per Gaia, només s'han d'utilitzar camps Gaia realment disponibles en el
model o dataset de TerraLab3D.

Per OpenNGC, només s'han d'utilitzar camps OpenNGC realment disponibles.

No s'han d'inventar propietats amb l'únic objectiu d'omplir la
interfície.

Els filtres específics han de quedar subordinats al tipus
d'objecte/catàleg corresponent i no desplaçar innecessàriament els
filtres comuns.

## Resultats

Els resultats es presenten com una llista de **targetes compactes**.

Cada targeta ha de permetre identificar ràpidament l'objecte i
valorar-ne l'observabilitat.

Informació potencial segons disponibilitat:

``` text
Nom
Tipus
Catàleg / identificador
Magnitud
Constel·lació
Altitud
Sortida
Posta
Mida angular
Qualitat d'observació
Mini gràfic d'altitud
```

No tots els camps són aplicables a tots els objectes.

La presentació s'ha d'adaptar a les dades disponibles sense mostrar
camps ficticis o buits de manera sorollosa.

## Identitat visual de les targetes

Quan un objecte **no disposa d'imatge**, la targeta utilitza una icona
identificativa a l'esquerra.

La icona pot utilitzar el color associat al tipus d'objecte.

``` text
[icona]  M42
         Nebulosa d'Orió
         ...
```

Quan existeix una fotografia adequada:

``` text
[foto]   M42
         Nebulosa d'Orió
         ...
```

la fotografia substitueix aquesta funció identificativa.

No s'ha d'afegir una segona decoració de color o icona només per repetir
el tipus si la fotografia ja compleix aquesta funció.

Les targetes no han de convertir-se en blocs de color sòlid segons el
tipus d'objecte.

## Sortida i posta

Les targetes han d'incloure, quan sigui aplicable, informació compacta
de sortida i posta.

Es poden utilitzar icones diferenciades acompanyades de l'hora.

Exemple conceptual:

``` text
↑ 20:43     ↓ 05:17
```

La informació ha de correspondre a la data/localització de l'observador
i integrar-se amb el mateix model temporal utilitzat per la resta de
TerraLab3D.

## Mini gràfic d'altitud

Cada resultat que disposi d'una trajectòria celeste calculable pot
mostrar un gràfic compacte d'altitud en funció del temps.

``` text
altitud
 90° │
     │        ╭──────╮
     │      ╭─╯      ╰─╮
     │    ╭─╯          ╰─╮
  0° ┼────╯──────────────╰────
-10° │
     └──────────────────────── temps
```

Eix X:

``` text
temps
```

Eix Y aproximat:

``` text
-10° → +90°
```

El gràfic ha de permetre entendre d'un cop d'ull:

- quan surt l'objecte;
- quan guanya altitud;
- quan arriba al màxim;
- quan baixa;
- quan es pon;
- si supera l'altitud mínima seleccionada.

Ha de ser un component lleuger i no provocar càlculs redundants per
frame.

## Qualitat d'observació

La cerca avançada ha de poder proporcionar un indicador de qualitat
d'observació.

Aquest indicador ha de servir tant per informar l'usuari com per ordenar
resultats.

L'ordenació per defecte prevista és:

``` text
qualitat d'observació
```

La qualitat no ha de ser un valor arbitrari de UI: ha de derivar de
criteris astronòmics disponibles a TerraLab3D.

Quan la qualitat sigui baixa, la targeta pot mostrar una causa resumida,
per exemple si el problema deriva de baixa altitud o d'un altre criteri
objectivament calculat.

La fórmula definitiva de qualitat s'ha de definir amb criteris explícits
i comprovables abans de considerar aquesta part completada.

## Ordenació

El sistema ha de permetre ordenar els resultats.

Criteris previstos:

- [ ] Qualitat d'observació.
- [ ] Nom.
- [ ] Magnitud.
- [ ] Altitud màxima.
- [ ] Hora de sortida.
- [ ] Hora de posta.

La qualitat d'observació és el criteri per defecte previst.

L'arquitectura ha de permetre afegir nous criteris sense acoblar-los a
la representació visual de les targetes.

## Interacció resultat ↔ cel

La finestra ha de romandre oberta mentre l'usuari explora resultats.

Les accions sobre un resultat han d'integrar-se amb els mecanismes
existents de selecció, centrat, picking i fitxa de TerraLab3D.

La implementació concreta de gestos ---click, doble click, hover o
controls explícits--- s'ha d'alinear amb les convencions ja existents de
TerraLab3D i evitar duplicar accions equivalents.

La cerca no ha de crear un segon sistema de selecció independent.

## Mostrar només els resultats al cel

A la part inferior de la finestra hi ha un control persistent equivalent
a:

``` text
☐ Mostrar només els resultats al cel
```

La redacció definitiva pot ajustar-se durant la implementació, però la
semàntica és fixa.

### Desactivat

El cel manté la representació normal.

Els resultats poden utilitzar els mecanismes habituals de selecció o
ressaltat.

### Activat

Els objectes que **no compleixen els filtres desapareixen** de la
representació corresponent.

``` text
catàleg visible
      ↓
màscara de resultats
      ↓
només coincidències visibles
```

No es tracta d'atenuar els objectes no coincidents.

No es tracta de reduir-ne simplement l'opacitat.

L'objectiu és l'aïllament visual dels resultats.

## Filtratge visual i GPU

Per conjunts molt grans, especialment Gaia, el mode d'aïllament no ha de
provocar reconstruccions completes del catàleg cada vegada que canvia un
filtre.

S'ha d'aprofitar l'arquitectura de buffers persistents de TerraLab3D.

Quan una propietat compacta sigui necessària per al filtratge massiu en
shader, pot formar part dels atributs GPU persistents.

El Pas 24 ja permet, per exemple, disposar d'un `constellation_id`
compacte per estrella.

Conceptualment:

``` text
CPU
 ├── metadades de cerca
 └── estat dels filtres
          ↓
     criteris/màscara
          ↓
GPU persistent
 ├── posició
 ├── magnitud
 ├── color
 ├── catalog_index
 └── metadades compactes necessàries
          ↓
shader
          ↓
visible / descartat
```

No s'han d'enviar milions de registres textuals o estructures de cerca a
GPU.

La frontera CPU/GPU s'ha de decidir segons el cost real i la necessitat
del filtre.

## Arquitectura funcional

``` text
                   Advanced Search UI
                          │
                          ▼
                   Search State/DTO
                          │
                          ▼
              AstronomicalSearchCoordinator
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
        Gaia           OpenNGC        Sistema Solar
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                  resultats unificats
                          │
               ┌──────────┼──────────┐
               ▼          ▼          ▼
            targetes   ordenació   cel
                                      │
                                      ▼
                              aïllament visual
```

Els catàlegs no han de conèixer la finestra.

El frontend no ha de consultar directament Gaia, OpenNGC ni els
adaptadors d'infraestructura.

## Tasques

- [ ] Definir l'estat/DTO de cerca avançada.
- [ ] Definir un model unificat de resultat de cerca.
- [ ] Estendre `AstronomicalSearchCoordinator` sense introduir
    dependències de presentació.
- [ ] Integrar estrelles Gaia.
- [ ] Integrar objectes OpenNGC.
- [ ] Integrar objectes del Sistema Solar.
- [ ] Implementar accés a «Cerca avançada» des del desplegable de
    cerca ràpida.
- [ ] Mostrar «Cerca avançada» com a primera opció abans d'escriure.
- [ ] Mostrar «Cerca avançada» al final quan ja existeixen resultats
    de cerca ràpida.
- [ ] Implementar finestra flotant no modal.
- [ ] Fer la finestra arrossegable des de la barra de títol.
- [ ] Mantenir la finestra oberta mentre s'interactua amb el cel.
- [ ] Implementar panell/corredor de filtres desplegable cap a
    l'esquerra.
- [ ] Permetre plegar el panell sense ocultar els resultats.
- [ ] Mantenir una disposició estable dels filtres.
- [ ] Implementar scroll independent dels resultats.
- [ ] Mantenir fix el control inferior d'aïllament visual.
- [ ] Implementar filtratge en viu.
- [ ] No implementar botó «Aplicar filtres».
- [ ] Implementar «Netejar filtres».
- [ ] Implementar selecció de tipus d'objecte.
- [ ] Definir explícitament la semàntica de «cap» i «tots» els tipus.
- [ ] Implementar filtre per constel·lació.
- [ ] Utilitzar `constellation_id` persistent per Gaia.
- [ ] Implementar filtre de magnitud/brillantor quan sigui aplicable.
- [ ] Implementar altitud mínima.
- [ ] Implementar interval temporal.
- [ ] Implementar acció ràpida «Ara».
- [ ] Implementar filtre de mida angular.
- [ ] Integrar filtratge per FOV amb el model instrumental existent.
- [ ] Evitar duplicar focal, sensor o FOV dins de la cerca.
- [ ] Implementar «Més filtres».
- [ ] Utilitzar només propietats reals de Gaia als filtres Gaia.
- [ ] Utilitzar només propietats reals d'OpenNGC als filtres OpenNGC.
- [ ] Implementar targetes compactes de resultat.
- [ ] Implementar icona per tipus quan no existeixi fotografia.
- [ ] Utilitzar fotografia en substitució de la icona identificativa
    quan existeixi.
- [ ] Evitar targetes de color sòlid per tipus.
- [ ] Mostrar sortida i posta quan sigui aplicable.
- [ ] Implementar mini gràfic altitud/temps.
- [ ] Fer que el gràfic reflecteixi l'interval temporal seleccionat.
- [ ] Fer visible la superació o no de l'altitud mínima.
- [ ] Definir el model de qualitat d'observació amb criteris
    científics explícits.
- [ ] Mostrar indicador de qualitat.
- [ ] Mostrar causa resumida quan la qualitat sigui baixa.
- [ ] Ordenar per qualitat d'observació per defecte.
- [ ] Implementar ordenació per nom.
- [ ] Implementar ordenació per magnitud.
- [ ] Implementar ordenació per altitud màxima.
- [ ] Implementar ordenació per sortida/posta.
- [ ] Connectar les targetes amb la selecció/picking existent.
- [ ] Permetre centrar/explorar resultats sense tancar la finestra.
- [ ] Implementar «Mostrar només els resultats al cel».
- [ ] Fer desaparèixer els objectes no coincidents quan l'aïllament és
    actiu.
- [ ] No substituir l'aïllament per una simple atenuació.
- [ ] Restaurar immediatament la representació normal en
    desactivar-lo.
- [ ] Evitar reconstruccions completes dels buffers Gaia per cada
    canvi de filtre.
- [ ] Determinar quins criteris convé resoldre en CPU i quins en GPU.
- [ ] Reutilitzar atributs GPU persistents compactes quan sigui
    justificat.
- [ ] Cancel·lar/invalidar consultes o càlculs obsolets quan els
    filtres canvien ràpidament.
- [ ] Mantenir fluida la càmera i el renderitzat durant
    actualitzacions de cerca.
- [ ] Mesurar rendiment amb catàlegs densos i actualització contínua
    de filtres.

## Criteri de sortida

L'usuari pot entrar a la cerca avançada des de la cerca ràpida, mantenir
una finestra flotant oberta mentre utilitza el cel, combinar filtres i
veure els resultats actualitzar-se en viu.

Els resultats integren Gaia, OpenNGC i Sistema Solar sota un model
coherent, respectant les propietats realment disponibles de cada font.

Les targetes proporcionen informació suficient per valorar l'observació,
incloent altitud, sortida/posta i evolució temporal quan sigui
aplicable.

La constel·lació pot utilitzar-se com a filtre sense recalcular la
classificació de les estrelles Gaia.

L'usuari pot activar l'aïllament visual i fer desaparèixer del cel els
objectes que no compleixen els criteris.

La cerca i els canvis de filtre no bloquegen la càmera ni introdueixen
reconstruccions massives evitables dels catàlegs residents.

## Evidència obligatòria

- [ ] Prova d'accés des de la cerca ràpida abans d'escriure.
- [ ] Prova d'accés des de la cerca ràpida amb resultats existents.
- [ ] Vídeo de la finestra flotant arrossegant-se mentre el cel
    continua interactiu.
- [ ] Vídeo d'obertura i plegat del panell lateral de filtres.
- [ ] Prova de filtratge en viu sense botó «Aplicar».
- [ ] Prova de combinació de diversos filtres.
- [ ] Prova de filtre per constel·lació sobre Gaia.
- [ ] Verificació que el filtre Gaia no executa classificació de
    constel·lacions en runtime.
- [ ] Prova de filtre per altitud mínima.
- [ ] Prova d'interval temporal.
- [ ] Prova de l'acció «Ara».
- [ ] Prova de mida angular/FOV.
- [ ] Prova dels filtres específics Gaia implementats.
- [ ] Prova dels filtres específics OpenNGC implementats.
- [ ] Prova de targeta sense fotografia.
- [ ] Prova de targeta amb fotografia.
- [ ] Prova de sortida i posta.
- [ ] Validació numèrica del mini gràfic d'altitud contra efemèrides
    calculades.
- [ ] Prova de qualitat d'observació i causa de qualitat baixa.
- [ ] Prova de totes les ordenacions implementades.
- [ ] Prova d'interacció successiva amb diversos resultats sense
    tancar la finestra.
- [ ] Prova d'activació de «Mostrar només els resultats al cel».
- [ ] Verificació visual que els no coincidents desapareixen i no
    només s'atenuen.
- [ ] Prova de restauració del cel en desactivar l'aïllament.
- [ ] Prova de canvis ràpids de filtres amb invalidació de treball
    obsolet.
- [ ] Mesura de frame rate amb camp Gaia dens i finestra oberta.
- [ ] Mesura de frame rate durant canvis continus de filtres.
- [ ] Verificació que no es reconstrueix el catàleg complet per cada
    canvi quan existeix una via persistent més eficient.

## Fora d'abast del pas

No es redissenya el sistema instrumental de telescopi, sensor o FOV; la
cerca consumeix les seves dades quan les necessita.

No s'implementa un planificador nocturn complet ni una seqüència
automàtica d'observació.

No es modifica el model científic de contaminació lumínica, extinció
atmosfèrica o altres factors més enllà d'utilitzar els valors que
TerraLab3D ja pugui proporcionar per a l'observabilitat.

No es creen camps ficticis de Gaia o OpenNGC per ampliar artificialment
la llista de filtres.

No es crea un segon sistema de picking o selecció independent del ja
existent.

No es recalculen les constel·lacions Gaia durant la cerca.

No es reconstrueixen buffers massius únicament per implementar
l'aïllament visual si aquest es pot resoldre amb l'arquitectura
persistent existent.

No es tanca, col·lapsa ni minimitza automàticament la finestra quan
l'usuari selecciona o explora un resultat.
