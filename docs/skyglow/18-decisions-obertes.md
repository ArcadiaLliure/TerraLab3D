# Decisions obertes del skyglow

Aquest registre conserva la traçabilitat històrica, però els bloquejos nous són **per domini S/C/H** segons la [política RSR](20-politica-rsr-i-validacio-per-dominis.md): la RSR absent impedeix afirmar H per al període, no desenvolupar S/SG-REF.

| ID | Pregunta | Resolució executable i estat | Pas |
|---|---|---|---:|
| DATA-VNP46 | Producte/release i política temporal v1 | **Documentat històricament:** `VNP46A2.002`, capa diària sense gap-fill, unitats/QA/llicència al [perfil v1](skyglow-v1-profile.json). La revisió multisatèl·lit no amplia retrospectivament la validació de 7.1/7.2. | 7.1 |
| DNB-2017 | Canvi de baixa radiància al voltant de 2017 | **Documentat:** comparació feble pre/post-2017 no validada; cap correcció universal. La validació del grànul és 7.2. | 7.1–7.2 |
| LOW-RAD | Negatius/prop de zero/no fiables | **Documentat:** preservar cru; fill/negatius/QA degradada fora de la inferència; cap `max(0,·)` silenciós. | 7.1–7.2 |
| V1 | Política PASS/FAIL i valors per gate | **Política preregistrada a 7.1.** Valors justificats al primer gate que els aplica: error espectral 7.4, transport zenital 7.12, empíric clear-sky 7.17 i SLO de producte 7.22. 7.28 només els consumeix. La manca d'un valor bloqueja aquell gate, no 7.2 ni 7.3. Les especificacions de detecció NASA no substitueixen aquests criteris. | 7.1; 7.4, 7.12, 7.17, 7.22; consum 7.28 |
| S1 | Oracle del gate zenital | **Executable a 7.6:** GK21 + àrea GL independents del futur runtime; domini pla homogeni i [convergència verificada](../evidencies/pas7.6/validacio-sg-ref.md), sense dependència de 7.65. Ampliació/revalidació exigida per a nous dominis. | 7.1 i 7.6 |
| F5 | Biaix single-scattering | **Quantificat a 7.6 en nou benchmarks plans homogenis:** Monte Carlo invers d'ordre superior, errors estàndard aparellats i cota de cua. [Resultats i límits](../evidencies/pas7.6/validacio-sg-ref.md); no cota universal urbana ni correcció per a C/H. | 7.1 i 7.6 |
| F7 | Radi màxim de fonts | **Decidit:** radi adaptatiu per cota d'error, sense tall fix arbitrari. | 7.1 |
| F6 | Magnitud perceptiva nocturna | **Fora de v1** mentre no s'exposi una magnitud única; el model futur requereix decisió pròpia. | 7.1 |
| DNB-RSR-ANNUAL | Resposta efectiva SNPP anual de 2026 | RSR anual exacta no exigida per S/C; referència del mateix sensor amb limitacions explícites. H continua requerint evidència instrumental. | 7.5.1 C; 7.17/7.24 H |
| DATA-MULTISAT | Quines fonts Black Marble C2 són candidates? | VNP46 preservat; adaptador NOAA-20 verificat amb grànul real a 7.5.1. VJ246 continua sense grànul inspeccionat. Adquisició comuna a 24. | 7.5.1; 24 |
| DNB-TOA-L3 | Com es relacionen l'operador TOA i la radiància L3? | **Contracte de mesura resolt a 7.3:** la [User Guide C2 §2.2 Eq. (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) documenta la correcció de `L_DNB` a `L_NTL`, i la secció 5.2 n'identifica la capa L3. La mateixa unitat no fa TOA=L3 i el L3 sol no permet reconstruir cada correcció. **Pendent per C/H:** RSR/guany aplicables, inferència SPD/angular observacional i incertesa. | 7.3 resolt; 7.16–7.24 pendents |
| DNB-J2-HGS | Pot MGS representar HGS a NOAA-21? | **Candidat oficial, no homologat:** el README DAWG V2 recomana MGS com a proxy d'HGS no mesurada; manca cota numèrica del desajust i mapping acreditat amb `VJ246A2.002` de 2026. NOAA-20 té MGS V1 heretada; no s'hi trasllada automàticament el proxy J2. El manifest 7.3 conserva l'estat diagnòstic. | 7.16 C; 7.17/7.24 H |
| SOURCE-SELECT | Prioritat NOAA-20/NOAA-21 i fallback | **Pendent:** admissibilitat per dia/AOI/QA/model; prioritat basada en cobertura Black Marble, qualitat i calibratge verificats. QA 0 del tile VJ146 h18v04 acredita qualitat local, no admissibilitat espectral. No usar la prioritat general de NOAA com a prioritat del producte NASA. Fallback explícit i provenance; cap suma entre sensors ni SBAF per defecte. Wizard/adquisició al Pas 24. | 7.16–7.24; 24 |
| V3 | Homologació del SpectralBandSet | **Resolució acotada a 7.4:** TerraLab3D ha [aprovat i congelat `0,01 mag`](../evidencies/pas7.4/criteri-preregistrat-v1.json) abans de la comparació. El [bandset adaptatiu](../evidencies/pas7.4/homologacio-bandset-v1.md) passa 238/238 integrals del domini tabulat v1; les RSR històriques continuen diagnòstiques. Absorció/dispersió de 7.10 i projeccions de 7.14 repeteixen el gate; una fallada exigeix versionar el bandset, sense relaxar el criteri. | 7.4 completat; revalidació 7.10/7.14 |
| F1 | Model espectral/angular de font i inversió des de L3 | S completat a 7.5; C relatiu executable a 7.5.1 amb mescles/angles hipotètics; incertesa propagada i H pendents. | 7.5; 7.5.1; 7.16–7.24 |
| SOURCE-TRACKS | Com evitar el bloqueig per RSR? | S/C comparteixen contracte i futur motor. NOAA-20 MGS de referència i LGS de sensibilitat; cap certificació nocturna 2026. | 7.5.1; 7.6; 7.28 |

## Regles

- Cap pas posterior pot “tancar” retroactivament una decisió que era prerequisit.
- Cap llindar PASS/FAIL es pot ajustar després de veure el resultat del candidat que ha de validar; qualsevol revisió s'aplica només prospectivament.
- Cada llindar requereix mètrica, unitat, domini, propietari, congelació i origen declarat: literatura/font metrològica, incertesa demostrada d'un oracle, requisit de producte aprovat o convergència justificada científicament. Constants «raonables» sense procedència són prohibides.
- Els valors numèrics es congelen abans de la primera decisió que els usa. El pressupost de 7.4 precedeix la selecció de bandes; la tolerància de 7.12 pot usar convergència/incertesa SG-REF de 7.6, mai residuals del runtime; els criteris de 7.17 precedeixen el conjunt reservat i incorporen incerteses instrumental, de dades i del model; els SLO de 7.22 són requisits aprovats de TerraLab3D previs a la decisió LUT/precomputació/FFT. Si falta evidència, es bloqueja només aquell pas. 7.28 no crea ni modifica criteris.
- Runtime↔SG-REF valida implementació/transport; no valida per si sol VNP46→emissió.
- Quadtree, Legendre, AD, cache i LUT/FFT són acceleracions posteriors al baseline directe.

Decisions tancades a 7.5.1: rang K 2.800–6.500, família estable CIE B1–B5, CCT efectiva resolta en uv, quatre normalitzacions, ensemble determinista de pesos radiants explícits, RSR MGS/LGS com a aproximació. Pendents: dades locals de tecnologies, SPD verificades de mercuri/LPS/ambre, escala absoluta, mapping HGS/L3, propagació i validació empírica.

**Actualització7.12,2026-10-19:** V1 té [criteri de transport congelat i verificat](../evidencies/pas7.12/validacio-gate-transport.md) només per al domini registrat. S1 s'amplia amb SG-REF espectral variable i terreny independents. La cota exterior és condicionada, no observacional. Els valors empírics7.17 i SLO7.22 continuen pendents; no es relaxa cap llindar retrospectivament.
