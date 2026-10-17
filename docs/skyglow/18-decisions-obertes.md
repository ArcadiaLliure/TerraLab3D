# Decisions obertes del skyglow

Aquest registre continua sent autoritatiu, però cap decisió bloquejant pot quedar “oberta” mentre Codex avança. Cada fila té ara un **pas de resolució**. Si en aquell pas manca evidència suficient, l’estat és `bloquejat` i no s’avança.

| ID | Pregunta | Resolució executable | Pas |
|---|---|---|---:|
| DATA-VNP46 | Producte/release i política temporal v1 | congelar al manifest v1 amb unitats/quality/llicència verificades | 7.1 |
| DNB-2017 | Canvi de baixa radiància al voltant de 2017 | política versionada per producte/release, sense correcció universal implícita | 7.1–7.2 |
| LOW-RAD | Negatius/prop de zero/no fiables | política explícita del manifest; mai `max(0,·)` silenciós | 7.1–7.2 |
| V1 | Llindars PASS/FAIL | preregistrar origen i valor abans dels benchmarks/gates | 7.1 |
| S1 | Oracle del gate zenital | **SG-REF propi del skyglow**; no dependència amb 7.65 | 7.1 i 7.6 |
| F5 | Biaix single-scattering | quantificar offline amb SG-REF/oracle més ric; no calibratge opac | 7.1 i 7.6 |
| F7 | Radi màxim de fonts | radi adaptatiu per cota d’error, no tall fix arbitrari | 7.1 |
| F6 | Magnitud perceptiva nocturna | no bloqueja v1 si no s’exposa una magnitud única; qualsevol model perceptiu futur requereix decisió pròpia | 7.1 |
| V3 | Homologació del SpectralBandSet | selecció per error contra espectre fi, mai per benchmark de temps | 7.4 |
| F1 | Emissió angular des de VNP46 quasi-nadir | model publicat/empíric/ensemble amb domini i incertesa; Lambert no és default | 7.5 |

## Regles

- Cap pas posterior pot “tancar” retroactivament una decisió que era prerequisit.
- Els llindars científics no es poden canviar després de veure el resultat del gate.
- Runtime↔SG-REF valida implementació/transport; no valida per si sol VNP46→emissió.
- Quadtree, Legendre, AD, cache i LUT/FFT són acceleracions posteriors al baseline directe.
