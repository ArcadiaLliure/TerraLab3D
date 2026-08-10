# TerraLab3D

TerraLab3D és una aplicació d’exploració astronòmica i geogràfica que permet observar el cel des de qualsevol punt del planeta dins d’un entorn tridimensional format pel cel, l’horitzó i el territori real que envolta l’observador.

L’usuari pot situar-se en unes coordenades concretes, escollir una data i una hora i explorar com es veurien el firmament, el relleu, els astres i les condicions d’observació des d’aquell lloc.

## Funcionalitats

### Observació des de qualsevol ubicació

TerraLab3D permet:

* establir la latitud i la longitud de l’observador;
* considerar l’altitud real del terreny;
* afegir una alçada addicional sobre el sòl;
* canviar d’ubicació i reconstruir l’escena corresponent;
* consultar el cel i l’horitzó des de qualsevol zona coberta per les dades disponibles;
* mantenir separades la posició geogràfica i l’altura efectiva de l’observador.

### Control de la data i l’hora

L’escena es pot consultar en temps real o en qualsevol altre moment.

L’usuari pot:

* activar el seguiment de l’hora actual;
* seleccionar manualment una hora del dia;
* avançar o retrocedir dies;
* escollir una data mitjançant un calendari;
* observar els canvis del cel al llarg de la nit;
* comparar l’hora local amb l’hora universal;
* veure com varien la posició dels astres i les condicions d’il·luminació amb el pas del temps.

### Cel astronòmic

TerraLab3D representa el firmament visible des de la ubicació i el moment seleccionats.

La representació pot incloure:

* estrelles;
* noms i informació dels astres;
* estrelles visibles a ull nu;
* estrelles febles accessibles amb instruments;
* objectes de cel profund;
* galàxies;
* nebuloses;
* cúmuls estel·lars;
* la Via Làctia;
* concentracions de pols interestel·lar;
* constel·lacions;
* objectes astronòmics cercables pel seu nom.

La quantitat d’estrelles visibles s’adapta a les condicions d’observació i als paràmetres seleccionats per l’usuari.

### Sistema solar

L’aplicació mostra la posició aparent dels principals objectes del sistema solar:

* el Sol;
* la Lluna amb superfície i libració físiques;
* Mercuri, Venus, Mart, Júpiter, Saturn, Urà i Neptú texturitzats i orientats;
* Plutó amb representació genèrica honesta quan no hi ha textura local;
* els anells A/B/C i la divisió de Cassini, alineats amb l’equador real de Saturn;
* el catàleg versionat dels 461 satèl·lits naturals planetaris coneguts a
  2026-07-09, amb posicions SPK per als 459 que disposen de kernel oficial;
* òrbites planetocèntriques mostrejades directament dels SPK.

Les seves posicions s’actualitzen segons la ubicació, la data i l’hora seleccionades.
Els recursos científics i les textures es resolen des de la biblioteca indicada
per `data_location.json`; no es dupliquen dins del repositori.

### Eclipsis i trajectòries aparents

TerraLab3D calcula amb SPICE la geometria topocèntrica dels eclipsis solars,
l'ombra terrestre dels eclipsis lunars, contactes refinats, separacions i
ocultacions sol·licitades. La classificació solar és local per observador i no
depèn de llindars d'obscuració. Les trajectòries aparents al cel són recursos
versionats diferents de les òrbites planetocèntriques SPK. Prop de la totalitat,
el limbe LRO/LOLA governa les Perles de Baily i l'anell de diamant; la corona
procedural queda marcada explícitament com a aproximada.

### Horitzó i relleu

TerraLab3D calcula l’horitzó real que envolta l’observador.

Això permet:

* representar el relleu en totes les direccions;
* identificar muntanyes, valls i obstacles geogràfics;
* comprovar quines zones del cel queden ocultes pel terreny;
* observar la silueta real de l’horitzó;
* modificar la distància de territori considerada;
* ajustar el nivell de precisió del perfil de l’horitzó;
* comparar el cel astronòmic amb el paisatge real de la ubicació.

### Representació tridimensional del territori

El territori es mostra com una superfície tridimensional contínua al voltant de l’observador.

L’usuari pot:

* activar o ocultar la topografia;
* activar o ocultar la superfície del territori;
* explorar el paisatge des de diferents orientacions;
* apropar-se o allunyar-se;
* modificar la direcció i l’elevació de la mirada;
* observar simultàniament el cel i el relleu;
* controlar fins a quina distància es representa el territori.

### Superfície terrestre

El relleu es pot recobrir amb diferents tipus d’informació visual:

* imatge aèria;
* ortofotografia;
* cobertura del sòl;
* classificació del territori;
* masses d’aigua;
* zones urbanes;
* boscos;
* cultius;
* terreny natural;
* altres categories geogràfiques disponibles.

L’usuari pot canviar entre una representació fotogràfica i una representació categòrica del territori.

També pot escollir entre:

* una visualització fidel als colors originals;
* una visualització més viva i contrastada.

### Gestió de capes

TerraLab3D permet activar, desactivar i combinar les diferents capes de l’escena.

Entre les capes disponibles hi pot haver:

* estrelles;
* objectes de cel profund;
* Via Làctia;
* pols interestel·lar;
* sistema solar;
* meteorologia;
* contaminació lumínica;
* horitzó;
* topografia;
* superfície terrestre.

El gestor de capes permet:

* veure quines capes estan disponibles;
* escollir les fonts utilitzades;
* afegir dades pròpies;
* descarregar recursos;
* enllaçar recursos existents;
* establir prioritats entre fonts;
* comprovar si una font cobreix la ubicació seleccionada;
* canviar de font sense alterar la resta de l’escena.

### Contaminació lumínica

L’aplicació simula l’impacte de la contaminació lumínica sobre el cel visible.

L’usuari pot treballar amb:

* estimació automàtica segons la ubicació;
* selecció manual de la classe de cel;
* límit manual de magnitud estel·lar;
* desactivació completa de l’efecte.

La contaminació lumínica modifica:

* la quantitat d’estrelles visibles;
* el contrast del cel;
* la visibilitat de la Via Làctia;
* la visibilitat dels objectes de cel profund;
* l’aspecte general del firmament.

### Condicions meteorològiques

TerraLab3D pot incorporar les condicions atmosfèriques de la ubicació seleccionada.

La representació meteorològica pot tenir en compte:

* nuvolositat;
* transparència atmosfèrica;
* estat general del cel;
* condicions que afecten l’observació astronòmica.

La capa meteorològica es pot activar o desactivar independentment de la resta de l’escena.

### Simulació visual

L’aplicació permet ajustar l’aspecte de les estrelles i del cel.

L’usuari pot modificar:

* la mida aparent de les estrelles;
* la intensitat de les puntes de difracció;
* l’ús de colors estel·lars més purs;
* el límit de magnitud;
* el nivell de contaminació lumínica;
* la quantitat d’elements visibles;
* la combinació de capes astronòmiques.

### Mode telescopi i càmera

TerraLab3D inclou un mode d’observació instrumental que delimita el camp visible d’un telescopi o d’una càmera.

L’usuari pot configurar:

* la distància focal;
* l’obertura de l’instrument;
* la relació focal;
* l’ocular;
* el tipus d’instrument;
* una càmera de sensor APS-C;
* una càmera de format complet;
* la sensibilitat ISO;
* el temps d’exposició;
* un camp de visió circular;
* un camp de visió rectangular;
* la relació d’aspecte;
* la velocitat de moviment.

Aquest mode permet simular l’enquadrament aproximat d’un objecte abans d’una observació o sessió d’astrofotografia.

### Navegació per coordenades astronòmiques

L’usuari pot introduir coordenades d’ascensió recta i declinació per dirigir la vista cap a una regió concreta del cel.

També pot:

* consultar les coordenades del centre de la vista;
* centrar un objecte astronòmic;
* seguir una posició celeste;
* ajustar manualment l’enquadrament;
* moure’s pel firmament a diferents velocitats.

### Cerca d’objectes

TerraLab3D permet cercar objectes astronòmics pel seu nom.

La cerca pot incloure:

* estrelles amb nom propi;
* objectes de cel profund;
* objectes catalogats;
* planetes;
* altres elements disponibles a l’escena.

Quan se selecciona un resultat, l’aplicació orienta la vista cap a la seva posició.

### Traços circumpolars

L’aplicació pot representar el moviment aparent de les estrelles al voltant del pol celeste.

Aquesta funció permet:

* iniciar una simulació circumpolar;
* alinear la vista amb el pol celeste corresponent;
* observar la trajectòria aparent de les estrelles;
* estudiar el moviment del firmament durant la nit;
* previsualitzar composicions de fotografia de traços estel·lars.

### Mesures sobre el cel

TerraLab3D incorpora eines per mesurar regions i separacions angulars.

Les eines disponibles inclouen:

* regle;
* quadrat;
* rectangle;
* cercle.

Aquestes eines permeten:

* mesurar la separació entre objectes;
* delimitar una zona del cel;
* comparar camps de visió;
* estimar l’enquadrament d’una observació;
* conservar diverses mesures sobre l’escena;
* eliminar les mesures quan ja no siguin necessàries.

### Creació de constel·lacions personalitzades

L’usuari pot dibuixar les seves pròpies figures sobre el firmament.

TerraLab3D permet:

* crear una constel·lació nova;
* posar-li un nom;
* seleccionar estrelles;
* unir estrelles mitjançant segments;
* crear diversos grups independents;
* mostrar o ocultar les figures;
* modificar una constel·lació existent;
* canviar-ne el nom;
* eliminar elements seleccionats;
* eliminar totes les constel·lacions personalitzades.

### Exploració integrada del cel i la Terra

La finalitat principal de TerraLab3D és permetre que l’usuari estudiï conjuntament:

* què hi ha al cel;
* on apareixerà cada objecte;
* quan serà visible;
* a quina altura es trobarà;
* en quina direcció s’haurà de mirar;
* si el relleu n’impedirà la visió;
* quina contaminació lumínica hi haurà;
* quines condicions meteorològiques poden afectar l’observació;
* quin enquadrament oferirà un telescopi o una càmera.

## Usos principals

TerraLab3D està orientat a:

* planificació d’observacions astronòmiques;
* preparació de sessions d’astrofotografia;
* estudi de l’horitzó d’una ubicació;
* cerca d’emplaçaments d’observació;
* simulació de camps de visió;
* identificació d’objectes celestes;
* estudi del moviment aparent del firmament;
* comparació de dates, hores i ubicacions;
* anàlisi de la contaminació lumínica;
* exploració educativa del cel i del territori;
* creació de representacions astronòmiques personalitzades.

## Estat del projecte

TerraLab3D es troba en desenvolupament actiu.

L’objectiu és reunir en una mateixa escena interactiva el territori, l’horitzó, el cel astronòmic i les condicions reals d’observació, mantenint una correspondència funcional amb TerraLab i ampliant-ne l’experiència d’exploració tridimensional.

## Crèdits i Llicències

* **Textures dels planetes del Sistema Solar**: Les textures utilitzades per als planetes estan basades en dades d'elevació i imatges públiques de la NASA (misions MESSENGER, Viking, Cassini i Telescopi Espacial Hubble) ajustades per [Solar System Scope](https://www.solarsystemscope.com/textures/). Distribudes sota la llicència **Creative Commons Attribution 4.0 International (CC BY 4.0)**.
* **Efemèrides i orientació**: kernels oficials [NAIF/JPL](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/) i contrast numèric amb [NASA/JPL Horizons](https://ssd.jpl.nasa.gov/horizons/).
* **Catàleg de satèl·lits naturals**: [JPL Solar System Dynamics](https://ssd.jpl.nasa.gov/sats/discovery.html), snapshot 2026-07-09.
