# Decisions obertes del skyglow

Aquest registre continua sent autoritatiu, però cap decisió bloquejant pot quedar “oberta” mentre Codex avança. Cada fila té ara un **pas de resolució**. Si en aquell pas manca evidència suficient, l’estat és `bloquejat` i no s’avança.

| ID | Pregunta | Resolució executable i estat | Pas |
|---|---|---|---:|
| DATA-VNP46 | Producte/release i política temporal v1 | **Documentat:** `VNP46A2.002`, capa diària sense gap-fill, unitats/QA/llicència al [perfil](skyglow-v1-profile.json). | 7.1 |
| DNB-2017 | Canvi de baixa radiància al voltant de 2017 | **Documentat:** comparació feble pre/post-2017 no validada; cap correcció universal. La validació del grànul és 7.2. | 7.1–7.2 |
| LOW-RAD | Negatius/prop de zero/no fiables | **Documentat:** preservar cru; fill/negatius/QA degradada fora de la inferència; cap `max(0,·)` silenciós. | 7.1–7.2 |
| V1 | Política PASS/FAIL i valors per gate | **Política preregistrada a 7.1.** Valors justificats al primer gate que els aplica: error espectral 7.4, transport zenital 7.12, empíric clear-sky 7.17 i SLO de producte 7.22. 7.28 només els consumeix. La manca d'un valor bloqueja aquell gate, no 7.2 ni 7.3. Les especificacions de detecció NASA no substitueixen aquests criteris. | 7.1; 7.4, 7.12, 7.17, 7.22; consum 7.28 |
| S1 | Oracle del gate zenital | **Decidit:** SG-REF propi del skyglow, sense dependència de 7.65; implementació a 7.6. | 7.1 i 7.6 |
| F5 | Biaix single-scattering | **Decidit:** contrast offline amb oracle d'ordre superior; quantificació a 7.6. | 7.1 i 7.6 |
| F7 | Radi màxim de fonts | **Decidit:** radi adaptatiu per cota d'error, sense tall fix arbitrari. | 7.1 |
| F6 | Magnitud perceptiva nocturna | **Fora de v1** mentre no s'exposi una magnitud única; el model futur requereix decisió pròpia. | 7.1 |
| V3 | Homologació del SpectralBandSet | **Pendent:** selecció per error contra espectre fi, mai per benchmark de temps. | 7.4 |
| F1 | Emissió angular des de VNP46 quasi-nadir | **Pendent:** model publicat/empíric/ensemble amb domini i incertesa; Lambert no és default. | 7.5 |

## Regles

- Cap pas posterior pot “tancar” retroactivament una decisió que era prerequisit.
- Cap llindar PASS/FAIL es pot ajustar després de veure el resultat del candidat que ha de validar; qualsevol revisió s'aplica només prospectivament.
- Cada llindar requereix mètrica, unitat, domini, propietari, congelació i origen declarat: literatura/font metrològica, incertesa demostrada d'un oracle, requisit de producte aprovat o convergència justificada científicament. Constants «raonables» sense procedència són prohibides.
- Els valors numèrics es congelen abans de la primera decisió que els usa. El pressupost de 7.4 precedeix la selecció de bandes; la tolerància de 7.12 pot usar convergència/incertesa SG-REF de 7.6, mai residuals del runtime; els criteris de 7.17 precedeixen el conjunt reservat i incorporen incerteses instrumental, de dades i del model; els SLO de 7.22 són requisits aprovats de TerraLab3D previs a la decisió LUT/precomputació/FFT. Si falta evidència, es bloqueja només aquell pas. 7.28 no crea ni modifica criteris.
- Runtime↔SG-REF valida implementació/transport; no valida per si sol VNP46→emissió.
- Quadtree, Legendre, AD, cache i LUT/FFT són acceleracions posteriors al baseline directe.
