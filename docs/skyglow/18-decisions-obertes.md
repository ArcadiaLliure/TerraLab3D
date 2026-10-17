# Decisions obertes del skyglow

Aquest registre conté decisions que **no** es poden tancar implícitament durant la implementació. La decisió ja presa és que VNP46 és la família de dades operativa, mentre VIIRS DNB continua essent el model de mesura espectral i el transport continua en el `PropagationKernel`.

| ID | Pregunta | Opcions | Conseqüències | Qui decideix | Dades necessàries |
|---|---|---|---|---|---|
| DATA-VNP46 | Quin producte/release VNP46 alimenta la v1 i amb quina política temporal? | producte anual estable / producte mensual / combinació versionada | estabilitat vs variació temporal; canvien qualitat i processament | responsable de dades + científic | documentació oficial, unitats, quality, correccions i llicència |
| F1 | Com s'infereix la distribució angular d'emissió des de VNP46 quasi-nadir? | model paramètric publicat / model empíric regional / ensemble | condiciona sobretot cúpules baixes i llarga distància | responsable científic | mesures angulars independents i informació d'apantallament/reflexió |
| F5 | Com es quantifica el biaix single-scattering? | A: `SG-REF` amb variant multiple-scattering pròpia; B: esperar el path tracer del Pas 7.65 i declarar dependència creuada | A desacobla però crea un solver offline; B reutilitza oracle però bloqueja homologació final | científic + arquitectura | cost de solver, fixtures i domini atmosfèric |
| F6 | Quina magnitud, si n'hi ha, representa percepció visual nocturna? | fotòpica+escotòpica / model mesòpic / cap magnitud perceptiva única | complexitat i risc de falsa interpretació | científic + producte | casos d'ús i norma CIE adoptada |
| F7 | Quin radi màxim de fonts s'utilitza? | fix / adaptatiu per cota d'error / perfils de qualitat | cost contra radiància omesa | científic + rendiment | convergència radial i distribució de fonts |
| V1 | Quins llindars fan PASS/FAIL? | preregistrar per referència publicada, requisit de producte o convergència numèrica | evita ajustar criteris després de veure resultats | producte + científic | requeriments i incerteses de referència |
| V3 | Com s'homologa un `SpectralBandSet`? | pressupost únic / pressupost per projecció / refinament fins convergència | determina error espectral sense escollir N per benchmark | científic | espectre fi, SPD adverses i toleràncies sensor |
| S1 | Quin oracle usa el gate 7.20? | A: pas propi `SG-REF`; B: dependència creuada amb 7.65 | A manté verticals separades; B simplifica oracles però bloqueja 7.20/7.21 | arquitectura + científic | cost, independència i calendari de 7.65 |
| DNB-2017 | Com es tracta el canvi de punt zero de baixa radiància al voltant de 2017? | restricció temporal sense correcció automàtica / paràmetre versionat per producte/release | afecta comparabilitat temporal de fonts febles | dades + científic | documentació/reprocessament i validació externa |
| LOW-RAD | Què es fa amb mesures negatives, prop de zero o no fiables? | excloure / propagar amb incertesa / política específica de producte | clipping pot eliminar fonts; conservar soroll pot crear cúpules espúries | científic de dades | distribució d'offset, quality flags i ground truth |

## Regles

- No es decideix Lambert per defecte.
- No es decideix una correcció universal pre/post-2017.
- No es decideix un llindar numèric sense origen.
- No es crea una FFT com a substitut de la física; només pot aparèixer com a acceleració validada.
- El Pas 7.20 no valida l'emissió; valida el transport donada l'emissió.
- El Pas 7.28 no pot homologar la vertical mentre una decisió bloquejant necessària per al domini declarat continuï oberta.
