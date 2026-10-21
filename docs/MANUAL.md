# TerraLab3D — Manual d'Operacions i Guia d'Usuari Avançat

> **Edició:** Manual Oficial del Sistema · Format Consola d'Operacions Astronòmiques.  
> **Estat del programari:** Versió viva operativa basada en mòduls científics i renderitzat 3D interactiu.

---

## Índex General de la Consola

- [1. Pròleg i Arquitectura de la Interfície](#1-pròleg-i-arquitectura-de-la-interfície)
- [2. Navegació 3D, Càmera i Modes de Desplaçament](#2-navegació-3d-càmera-i-modes-de-desplaçament)
- [3. 📍 Ubicació de l'Observador i Temps Astronòmic](#3--ubicació-de-lobservador-i-temps-astronòmic)
- [4. 🌌 El Cel: Atmosfera Física, Foscor Bortle i Il·luminació](#4--el-cel-atmosfera-física-foscor-bortle-i-il·luminació)
- [5. 🌌 El Cel: Catàleg Estel·lar Gaia DR3 & Picking d'Inspecció](#5--el-cel-catàleg-estel·lar-gaia-dr3--picking-dinspecció)
- [6. 🌌 El Cel: Sistema Solar — Sol, Lluna 8K, Planetes, Anells i Satèl·lits](#6--el-cel-sistema-solar--sol-lluna-8k-planetes-anells-i-satèl·lits)
- [7. 🌌 El Cel: Via Làctia, Pols Galàctica de Planck i Cel Profund NGC/IC](#7--el-cel-via-làctia-pols-galàctica-de-planck-i-cel-profund-ngcic)
- [8. 🌌 El Cel: Trajectòries de 24h i Visibilitat sobre l'Horitzó Real DEM](#8--el-cel-trajectòries-de-24h-i-visibilitat-sobre-lhoritzó-real-dem)
- [9. 🌌 El Cel: Traces Estel·lars i Exposició Temporal (Star Trails)](#9--el-cel-traces-estel·lars-i-exposició-temporal-star-trails)
- [10. ⛰️ Terra: Relleu DEM 3D, Horitzó Real Calculat i Cobertura de Superfície](#10-️-terra-relleu-dem-3d-horitzó-real-calculat-i-cobertura-de-superfície)
- [11. 📐 Eines: Modes d'Observació Instrumental (Òptica i Fotografia)](#11--eines-modes-dobservació-instrumental-òptica-i-fotografia)
- [12. 📐 Eines: Instruments de Mesura Esfèrica](#12--eines-instruments-de-mesura-esfèrica)
- [13. 🌌 Constel·lacions de referència i figures pròpies](#13--constellacions-de-referència-i-figures-pròpies)
- [Apèndix A — Taula de Dreceres de Teclat i Gestos Ràpids](#apèndix-a--taula-de-draceres-de-teclat-i-gestos-ràpids)
- [Apèndix B — Oracles de Càlcul Científic, Fonts de Dades i Toleràncies](#apèndix-b--oracles-de-càlcul-científic-fonts-de-dades-i-toleràncies)
- [Apèndix C — Preguntes Freqüents i Resolució d'Incidències (FAQ)](#apèndix-c--preguntes-freqüents-i-resolució-dincidències-faq)

---

## 1. Pròleg i Arquitectura de la Interfície

### 1.1. Què és TerraLab3D i per a què serveix

**TerraLab3D** és una estació de treball astronòmica i geogràfica tridimensional dissenyada per a la simulació, observació i anàlisi de la volta celeste en conjunció amb la topografia real de la Terra. A diferència dels planetaris convencionals que utilitzen horitzons plans artificials o fons bidimensionals, TerraLab3D integra models digitals d'elevació (DEM) reals amb càlculs d'efemèrides d'alta precisió (SPICE, DE440, Gaia DR3), permetent conèixer exactament com i quan un astre és visible des de qualsevol punt geogràfic del planeta.

### 1.2. Organització de la consola d'operacions

La interfície s'organitza en quatre àrees funcionals interconnectades en temps real:

![Organització de la interfície de TerraLab3D](examples/interficie/mapa-interficie.png)

![Vista general de la interfície](evidencies/interficie/interficie-general.png)

1. **Cúpula Celeste 3D (Espai Central):** Motor de renderitzat interactiu a 360° amb projecció perspectiva esfèrica, malles de terreny DEM d'alta resolució, estrelles Gaia, cossos del Sistema Solar i cel profund.
2. **Calaix de Menús Lateral (Menú d'Eines):** Desplegable amb quatre pestanyes especialitzades:
   - **📍 Ubicació:** Coordenades geodèsiques, elevació de l'observador, offsets d'ull i modes de navegació.
   - **🌌 Cel:** Control de física atmosfèrica, contaminació lumínica Bortle, Sistema Solar, Via Làctia, cel profund i trajectòries.
   - **⛰️ Terra (Topografia):** Gestió de malles DEM, perfil d'horitzó real calculat i cobertures de sòl.
   - **📐 Eines:** Simulació de sensors i òptiques (Ull nu, Càmera, Telescopi) i instruments de mesura esfèrica.
3. **HUD d'Inspecció i Estat (Inferior Esquerre):** Targeta telemètrica amb coordenades de l'observador, orientació de càmera (Az, Alt, FOV) i detall científic de l'astre seleccionat amb botons d'acció ràpida (*Centrar*, *Seguir*, *Alliberar*, *Netejar*).
4. **Línia Temporal de Simulació (Barra Inferior):** Control del rellotge astronòmic, temps universal (UTC), temps sideral local (LST), alçades solars, crepuscles i velocitat de reproducció.

### 1.3. Com funciona per dins

TerraLab3D implementa una arquitectura desacoblada:

- **Nucli Científic (Python):** Executa els models de mecànica celeste, rotació terrestre (IAU/IERS), integració de perfils d'horitzó i mostreig d'efemèrides.
- **Pont de Comunicació (WebSocket):** Transfereix dades d'estat i buffers binaris compactes (`ArrayBuffer`) amb sincronització asíncrona no blocant basada en generacions monotòniques (*latest-wins*).
- **Adaptador Visual (Three.js / WebGL):** Manté geometries retingudes, materials de shaders físics i renderitzat fluid a 60 fps.

**Passos d'origen:** [Pas 1 — Entorn 3D executable](tasques/completat/pas1.md), [Pas 4 — Grid celeste, brúixola i HUD](tasques/completat/pas4.md).

---

## 2. Navegació 3D, Càmera i Modes de Desplaçament

### 2.1. Què fa i per a què serveix

Permet a l'observador moure lliurement la visual per tota l'esfera celeste, desplaçar-se per la topografia del terreny, fer zoom sobre detalls astronòmics i bloquejar el seguiment automàtic de qualsevol cos celeste per compensar la rotació de la Terra.

### 2.2. Com s'utilitza: Comandaments i Gestos

| Comandament | Acció | Descripció operativa |
| :--- | :--- | :--- |
| **Clic esquerre + Arrossegar** | Girar mirada | Varia de forma contínua l'Azimut ($0^\circ \to 360^\circ$) i l'Altitud ($-90^\circ \to +90^\circ$). |
| **Roda del ratolí** | Zoom òptic | Modifica el camp de visió horitzontal ($\text{FOV}$) entre $1^\circ$ (detall planetari) i $100^\circ$ (gran angular). |
| **Clic sobre un astre** | Selecció + Seguiment | Centra l'astre, obre la fitxa al HUD i activa el mode `Seguint ✓`. |
| **Tecla `F`** | Mode Avió | Intercanvia entre Mode Avió i Mode Persona |
| **Tecles `W`, `A`, `S`, `D`** | Desplaçament | Mou la càmera en mode *Caminar* (sobre la cota del terreny) o en mode *Avió*. |
| **Tecla `Esc`** | Alliberar / Reset | Desactiva el seguiment de càmera actiu i retorna al mode d'Ull nu lliure. |

#### Modes de càmera (Pestanya 📍 Ubicació)

- **Mode Trípode / Ull nu (Fix):** La càmera roman fixa al punt d'observació geogràfic. Rotació pura en azimut i altitud.
- **Mode Caminar (First-person):** L'observador camina pel terreny. El sistema calcula en cada pas la cota del terreny DEM $z_{\text{DEM}}(x, y)$ i hi afegeix l'alçada d'ull (per defecte $1.70\text{ m}$).
- **Mode Avió / Vol lliure:** Desplaçament tridimensional ràpid per explorar carenes i valls amb transicions suaus.

### 2.3. Com funciona per dins: Cinemàtica i Seguiment

La càmera es defineix en coordenades topocèntriques locals **ENU** (*East-North-Up*). La direcció de la visual es calcula mitjançant el vector unitari:
$$\vec{v} = \begin{pmatrix} \cos(\text{alt}) \cdot \sin(\text{az}) \\ \cos(\text{alt}) \cdot \cos(\text{az}) \\ \sin(\text{alt}) \end{pmatrix}$$

Quan s'activa el seguiment (`focusTrackingController.startTracking`), el sistema resol a cada frame la posició topocèntrica de l'objecte objectiu $\vec{P}_{\text{target}}(t)$ i ajusta la matriu de rotació de la càmera mitjançant interpolació esfèrica de quaternions (Slerp), garantint un seguiment suau sense vibracions numèriques.

**Passos d'origen:** [Pas 1 — Càmera 360°](tasques/completat/pas1.md), [Pas 3.5 — Càmera translacional i modes de navegació](tasques/completat/pas3.5.md), [Pas 4 — HUD](tasques/completat/pas4.md), [Pas 12 — Cerca i seguiment](tasques/completat/pas12.md).

---

## 3. 📍 Ubicació de l'Observador i Temps Astronòmic

### 3.1. Què fa i per a què serveix

Defineix les coordenades geodèsiques i l'instant temporal exacte de la simulació. Permet situar l'observador a qualsevol punt de la superfície de la Terra i analitzar el cel en qualsevol data del passat o del futur amb màxima precisió sideral.

### 3.2. Com s'utilitza

1. Obriu la pestanya **📍 Ubicació** a la barra lateral.
2. Introduïu la **Latitud** (de $-90^\circ$ a $+90^\circ$) i la **Longitud** (de $-180^\circ$ a $+180^\circ$) en graus decimals.
3. El sistema obté automàticament l'elevació del terreny des del model DEM. Podeu afegir una **Alçada addicional** (alçada d'ull o torre d'observació).
4. A la línia temporal inferior, ajusteu l'hora amb la barra lliscant, activeu el mode **Temps real** o canvieu de data amb el calendari.
5. Activeu les caselles d'**Equador celeste**, **Grid azimut-altitud** o **Brúixola** per visualitzar les referències esfèriques.

![Esfera Celeste, Temps Sideral i Coordenades](examples/temps-coordenades.svg)

### 3.3. Com funciona per dins: Formulació Matemàtica

#### 1. Dia Julià ($JD$) i Segles Julians ($T$)

El temps universal coordinat ($UT$) es converteix en Dia Julià segons l'algorisme estàndard d'IAU/SOFA:
$$JD = \lfloor 365.25(Y+4716) \rfloor + \lfloor 30.6001(M+1) \rfloor + D + \frac{h + m/60 + s/3600}{24} + B - 1524.5$$
on $B = 2 - \lfloor Y/100 \rfloor + \lfloor Y/400 \rfloor$ per a dates gregorianes. El temps en segles julians des de l'època estàndard J2000.0 és:
$$T = \frac{JD - 2451545.0}{36525}$$

#### 2. Temps Sideral de Greenwich ($GMST$) i Local ($LST$)

Segons el model IAU, el Temps Sideral Mitjà de Greenwich a $0\text{h } UT$ es calcula com:
$$\theta_{GMST} = 280.46061837^\circ + 360.98564736629^\circ \cdot (JD - 2451545.0) + 0.000387933^\circ \cdot T^2 - \frac{T^3}{38710000}^\circ$$
El **Temps Sideral Local ($LST$)** a la longitud geogràfica $\lambda$ de l'observador s'obté sumant la longitud en unitats angulars:
$$LST = \left( \theta_{GMST} + \lambda \right) \pmod{360^\circ}$$

#### 3. Conversió de Coordenades Equatorials (ICRS) a Horitzontals Locals (ENU)

Donat un astre amb Ascensió Recta $\alpha$ i Declinació $\delta$, el seu **Angle Horari ($HA$)** és:
$$HA = LST - \alpha$$
L'**Altitud geomètrica ($h$)** i l'**Azimut astronòmic ($A$)** s'obtenen resolent el triangle astronòmic:
$$\sin h = \sin \phi \cdot \sin \delta + \cos \phi \cdot \cos \delta \cdot \cos HA$$
$$\cos A = \frac{\sin \delta - \sin \phi \cdot \sin h}{\cos \phi \cdot \cos h}, \quad \sin A = -\frac{\cos \delta \cdot \sin HA}{\cos h}$$
on $\phi$ és la latitud geogràfica de l'observador.

**Passos d'origen:** [Pas 2 — Ubicació geogràfica](tasques/completat/pas2.md), [Pas 3 — Rellotge de simulació i temps sideral](tasques/completat/pas3.md), [Pas 4 — Grid celeste i brúixola](tasques/completat/pas4.md).

---

## 4. 🌌 El Cel: Atmosfera Física, Foscor Bortle i Il·luminació

### 4.1. Què fa i per a què serveix

Simula la interacció de la llum solar i lunar amb l'atmosfera terrestre (dispersió de Rayleigh i Mie), reproduint amb fidelitat física el blau del cel diürn, els tons daurats i rogencs de les postes de sol, les fases crepusculars i l'impacte de la contaminació lumínica en la visibilitat de les estrelles.

### 4.2. Com s'utilitza

1. Aneu a la pestanya **🌌 Cel**.
2. **Atmosfera visual:** Activeu la casella *Atmosfera* per activar el càlcul de dispersió continu.
3. **Contaminació lumínica:**
   - Trieu el mode **Bortle** i seleccioneu una classe entre **1** (cel verge de muntanya o reserva astronòmica) i **9** (centre de gran metròpoli).
   - O trieu el mode **Magnitud** per fixar manualment el límit instrumental o visual d'extinció estel·lar (ex: $6.5\text{ mag}$).

![Calaix de control lateral amb la pestanya Cel oberta i paràmetres astronòmics](evidencies/interficie/calaix-pestanyes.png)

### 4.3. Com funciona per dins: Formulació Matemàtica

#### 1. Fases Crepusculars segons l'Altitud Solar ($h_\odot$)

La il·luminació i el color del cel s'avaluen contínuament en funció de l'altitud del centre del disc solar $h_\odot$:

- **Dia:** $h_\odot > 0^\circ$ (predomini de la dispersió de Rayleigh).
- **Crepuscle Civil:** $-6^\circ < h_\odot \le 0^\circ$ (l'horitzó terrestre és clarament visible; només destaquen Venus, Júpiter i estrelles de primera magnitud com Sírius o Vega).
- **Crepuscle Nàutic:** $-12^\circ < h_\odot \le -6^\circ$ (línia d'horitzó distingible al mar; apareixen les estrelles de navegació de segona magnitud).
- **Crepuscle Astronòmic:** $-18^\circ < h_\odot \le -12^\circ$ (el cel s'enfosqueix progressivament fins a l'extinció de tota llum solar residual).
- **Nit Fosca:** $h_\odot \le -18^\circ$ (la brillantor del cel queda determinada exclusivament per la llum zodiacal, la Lluna i la contaminació lumínica).

#### 2. Escala de Bortle i Magnitud Límit Visual ($m_{\text{lim}}$)

La relació entre la classe de l'escala de Bortle $B \in [1, 9]$ i la **Magnitud Límit Visual d'Ull Nu ($m_{\text{lim}}$)** s'expressa mitjançant el model fotomètric de Schäfer/TerraLab:
$$m_{\text{lim}} = 7.93 - 5 \log_{10}\left(1 + 10^{\frac{B - 1}{2}}\right)$$
La luminància de fons del cel $L_{\text{sky}}$ transmesa al shader en $\text{cd/m}^2$ s'utilitza com a llindar de tall en el renderitzat de punts estel·lars, atenuant o ocultant automàticament les estrelles la brillantor de les quals quedi per sota del fons contaminant.

**Passos d'origen:** [Pas 7 — Cel, atmosfera i Bortle](tasques/completat/pas7.md), [Pas 8.7 — Il·luminació física](tasques/completat/pas8.7.md).

---

## 5. 🌌 El Cel: Catàleg Estel·lar Gaia DR3 & Picking d'Inspecció

### 5.1. Què fa i per a què serveix

Projecta milions d'estrelles procedents del catàleg astromètric **Gaia DR3** de l'Agència Espacial Europea (ESA), calculant per a cadascuna la posició exacta, la magnitud aparent fotomètrica i el color real de cos negre basat en la temperatura efectiva. Permet fer clic sobre qualsevol estrella per inspeccionar-ne les dades telemètriques al HUD.

### 5.2. Com s'utilitza

1. Assegureu-vos que la capa d'**Estrelles** està activa a la pestanya **Cel**.
2. Feu clic sobre qualsevol estrella visible al cel 3D.
3. El HUD mostrarà a l'instant:
   - **Nom / Identificador de catàleg:** Ex: *Alpha Canis Majoris (Sirius)* o `Gaia DR3 302...`.
   - **Coordenades equatorials (ICRS):** Ascensió Recta ($\alpha$) i Declinació ($\delta$).
   - **Magnitud aparent ($G$ / $V$)** i índex de color fotomètric.
4. Premeu el botó **Seguint ✓** per mantenir l'estrella centrada mentre avança el temps.

### 5.3. Com funciona per dins: Geometria de Buffers i Colorimètria

#### 1. Buffers de GPU Retinguts

Les estrelles s'emmagatzemen a la memòria de la targeta gràfica en un únic `BufferGeometry` persistent amb atributs entrellaçats:

- `position`: Vector unitari cartesià $\vec{P} = (\cos \delta \cos \alpha, \cos \delta \sin \alpha, \sin \delta)$ en espai ICRS.
- `magnitude`: Magnitud fotomètrica en banda $G$ de Gaia en precisió `Float32`.
- `color`: Tripleta RGB de color físic en `Float32`.
- `catalogIndex`: Identificador únic en `Uint32` per al picking ràpid.

#### 2. Càlcul del Color Estel·lar a partir de l'Índex de Color ($B - V$)

L'índex de color fotomètric $B - V$ es converteix en **Temperatura Efectiva ($T_{\text{eff}}$)** en Kelvin utilitzant la relació analítica de Ballesteros:
$$T_{\text{eff}} = 4600 \text{ K} \left( \frac{1}{0.92(B - V) + 1.70} + \frac{1}{0.92(B - V) + 0.62} \right)$$
A partir de $T_{\text{eff}}$, la distribució espectral s'obté integrant la **Llei de Radiació de Planck**:
$$B_\lambda(T) = \frac{2 h c^2}{\lambda^5 \left( e^{\frac{h c}{\lambda k_B T}} - 1 \right)}$$
ponderada per les funcions de concordança de color estàndard CIE 1931 $(\bar{x}(\lambda), \bar{y}(\lambda), \bar{z}(\lambda))$ i convertida a l'espai de color sRGB lineal, garantint que les estrelles de tipus espectral O/B es mostrin blanc-blavoses ($10.000\text{ K} - 30.000\text{ K}$), les de tipus G groguenques ($5.800\text{ K}$) i les de tipus M ataronjades o vermelloses ($3.000\text{ K}$).

#### 3. Indexació Espacial de Picking en Temps $O(1)$

Per evitar consultes lentes per pas de raig (*raycasting*) sobre milions de vèrtexs, el mòdul `StarPickProvider` empra una estructura de partició espacial basada en **Hash de Cub-Esfera** (*cube-sphere hash*). El raig de la càmera es projecta a la cel·la de l'esfera, resolent la col·lisió de selecció en menys de $1\text{ ms}$ sense bloquejar la renderització.

**Passos d'origen:** [Pas 5 — Camp estel·lar Gaia](tasques/completat/pas5.md), [Pas 6 — Picking estel·lar](tasques/completat/pas6.md), [Pas 13 — Selecció i inspecció](tasques/completat/pas13.md).

---

## 6. 🌌 El Cel: Sistema Solar — Sol, Lluna 8K, Planetes, Anells i Satèl·lits

### 6.1. Què fa i per a què serveix

Renderitza amb màxima precisió astromètrica i fidelitat visual el Sol, la Lluna (amb textura d'albedo i relleu LOLA de la NASA en resolució 8K), els 8 planetes del Sistema Solar (Mercuri, Venus, Mart, Júpiter, Saturn amb anells 3D, Urà, Neptú i Plutó) i els seus 461 satèl·lits naturals coneguts amb efemèrides JPL/NAIF SPICE.

### 6.2. Com s'utilitza

1. A la pestanya **🌌 Cel**, a la secció **Sistema Solar**:
   - Activeu/desactiveu la visibilitat de planetes, òrbites SPK o etiquetes de satèl·lits.
   - Activeu la casella **Superfície LRO/LOLA** per gaudir de la Lluna fotorealista en 8K.
   - Filtreu els sistemes de satèl·lits actius (Mart, Júpiter, Saturn, Urà, Neptú, Plutó).
2. Feu clic sobre qualsevol planeta o lluna per centrar-lo i inspeccionar-ne el diàmetre aparent, la distància a la Terra i les coordenades topocèntriques.

### 6.3. Com funciona per dins: Efemèrides SPICE, Fases Físiques i Anells

#### 1. Efemèrides Planetàries d'Alta Precisió (JPL DE440 & SPICE Kernels)

La posició topocèntrica $\vec{r}_{\text{topo}}$ de cada cos celeste respecte a l'observador terrestre es calcula restant la posició geocèntrica de l'observador $\vec{R}_{\text{obs}}(t)$ de la posició geocèntrica del cos $\vec{r}_{\text{geo}}(t)$ obtinguda dels fitxers d'efemèrides del JPL:
$$\vec{r}_{\text{topo}}(t) = \vec{r}_{\text{geo}}(t) - \vec{R}_{\text{obs}}(t)$$

#### 2. Geometria de Fases i Libració Lunar Topocèntrica

La fase lunar no és una textura pintada, sinó que es genera dinàmicament a partir de l'**Angle de Fase Solar ($\Phi$)**:
$$\cos \Phi = \frac{\vec{r}_{\text{moon-sun}} \cdot \vec{r}_{\text{moon-obs}}}{\|\vec{r}_{\text{moon-sun}}\| \|\vec{r}_{\text{moon-obs}}\|}$$
La fracció il·luminada del disc visible és $k = \frac{1 + \cos \Phi}{2}$.  
La **libració lunar** (òptica en longitud $l$ i en latitud $b$, i física) s'avalua orientant l'esfera lunar 3D segons els angles d'Euler de rotació de la IAU (lleis de Cassini i nutació lunar), reflectint amb exactitud quin 59% de la superfície lunar és visible des de les coordenades de l'observador en cada moment.

#### 3. Inclinació Geomètrica dels Anells de Saturn

El pla dels anells de Saturn es defineix pel vector unitari del seu pol nord equatorial $\hat{n}_{\text{Saturn}}(\alpha_0, \delta_0)$. L'obertura o **inclinació aparent dels anells ($B$)** vista des de la Terra s'obté directament del producte escalar:
$$\sin B = \hat{n}_{\text{Saturn}} \cdot \frac{\vec{r}_{\text{Saturn-obs}}}{\|\vec{r}_{\text{Saturn-obs}}\|}$$

**Passos d'origen:** [Pas 8 — Sol, Lluna i planetes](tasques/completat/pas8.md), [Pas 8.5 — Superfície lunar LRO/LOLA](tasques/completat/pas8.5.md), [Pas 8.6 — Planetes, anells i satèl·lits](tasques/completat/pas8.6.md), [Pas 9 — Eclipsis i separacions](tasques/completat/pas9.md).

---

## 7. 🌌 El Cel: Via Làctia, Pols Galàctica de Planck i Cel Profund NGC/IC

### 7.1. Què fa i per a què serveix

Representa l'estructura a gran escala de la nostra galàxia i de l'univers profund: la panoràmica fotogràfica contínua de la Via Làctia a 360°, el mapa d'emissió tèrmica de pols interestel·lar capturat pel telescopi espacial Planck (ESA) i el catàleg complet OpenNGC/IC amb més de 13.000 nebuloses, galàxies i cúmuls estel·lars.

### 7.2. Com s'utilitza

1. La **Via Làctia** s'activa automàticament per defecte en iniciar l'aplicació.
2. A la pestanya **🌌 Cel**, activeu **Pols de Planck** per visualitzar els núvols de pols interestel·lar en infraroig.
3. Activeu la casella **Cel profund (NGC/IC)** per visualitzar nebuloses i galàxies amb etiquetes i imatges integrades.
4. Utilitzeu el cercador per trobar objectes emblemàtics (ex: *M31*, *M42*, *NGC 7000*, *NGC 7293*).

### 7.3. Com funciona per dins: Coordenades Galàctiques $(l, b)$

Les textures galàctiques s'orienten transformant de l'equador ICRS a les coordenades del pla galàctic mitjançant la matriu de rotació de la IAU (amb el pol nord galàctic a $\alpha = 192.85948^\circ, \delta = 27.12825^\circ$):
$$\begin{pmatrix} \cos b \cos(l - 33^\circ) \\ \cos b \sin(l - 33^\circ) \\ \sin b \end{pmatrix} = \begin{pmatrix} -0.054876 & -0.873437 & -0.483835 \\ 0.494109 & -0.444830 & 0.746982 \\ -0.867666 & -0.198076 & 0.455984 \end{pmatrix} \begin{pmatrix} \cos \delta \cos \alpha \\ \cos \delta \sin \alpha \\ \sin \delta \end{pmatrix}$$
El shader ajusta la brillantor i el contrast de la Via Làctia en funció de la classe Bortle de contaminació lumínica.

**Passos d'origen:** [Pas 10 — Via Làctia i Planck](tasques/completat/pas10.md), [Pas 11 — Cel profund NGC/IC](tasques/completat/pas11.md), [Pas 12 — Cerca astronòmica](tasques/completat/pas12.md).

---

## 8. 🌌 El Cel: Trajectòries de 24h i Visibilitat sobre l'Horitzó Real DEM

### 8.1. Què fa i per a què serveix

Projecta la trajectòria aparent de 24 hores cap endavant de qualsevol astre seleccionat, avaluant de forma rigorosa si en cada instant és visible o queda ocult darrere de les muntanyes i carenes del relleu local (DEM).

![Estats visuals de la trajectòria](examples/pas22/estats-trajectoria.png)

### 8.2. Com s'utilitza

1. Seleccioneu qualsevol cos celeste (Sol, Lluna, planeta, estrella o objecte NGC).
2. La casella **Trajectòria de l'objecte** a la pestanya **Cel** ve activada per defecte.
3. El sistema calcula la trajectòria per a un interval complet de **24 hores**.
4. **Conservació contínua de la línia:** Quan moveu la línia de temps o canvieu l'hora dins d'aquestes 24 hores, la línia de trajectòria es manté dibuixada sense parpellejos ni recàlculs innecessaris. El marcador lluminós de posició actual s'anima en temps real al llarg del traç.
5. Si desplaceu el temps més enllà de les 24 hores o canvieu d'astre o d'observador, el sistema recalcula automàticament el nou interval.

#### Llegenda de Visibilitat

- `━━━━` **Cian continu brillant:** Segment visible per sobre de les muntanyes.
- `┄ ┄ ┄` **Lila neó discontinu:** Segment ocult darrere del relleu 3D (visible clarament a través de les muntanyes).
- `┄ ┄ ┄` **Lila clar puntejat:** Segment situat per sota de l'horitzó pla a 0°.
- `┈ ┈ ┈` **Ambre puntejat:** Dades insuficients de perfil DEM.

| Enquadrament panoràmic complet: Trajectòria de 24h a la nit amb Alba i Posta simultànies |
| :---: |
| ![Trajectòria completa de 24h amb etiquetes d'alba i posta](evidencies/pas22/trajectoria-completa.png) |
| *Vista general nocturna en gran angular (FOV 115°) amb la Lluna en culminació meridional. En un únic enquadrament s'observa l'arc sencer de 24h, l'etiqueta d'Alba (`↑ Alba 17:00:27 · Az 126.5°`) a l'est, la de Posta (`↓ Posta 01:49:19 · Az 234.9°`) a l'oest i el traçat discontinu lila penetrant sota la línia de carena de les muntanyes.* |

### 8.3. Com funciona per dins: Refinament de Creuaments per Bisecció

El sistema mostreja la posició de l'astre en 128 intervals adaptatius i avalua la funció d'elevació aparent respecte a la silueta de l'horitzó $h_{\text{DEM}}(\text{az})$:
$$f(t) = \text{alt}_{\text{astre}}(t) - h_{\text{DEM}}(\text{az}(t))$$
Quan es detecta un canvi de signe $f(t_1) \cdot f(t_2) < 0$, el coordinador Python aplica un algorisme de **bisecció d'arrels** per determinar l'instant exacte del creuament $t^*$ amb precisió subsegon.

**Passos d'origen:** [Pas 9 — Trajectòries](tasques/completat/pas9.md), [Pas 15 — Perfil d'horitzó](tasques/completat/pas15.md), [Pas 22 — Trajectòries i visibilitat sobre l'horitzó real](tasques/completat/pas22-trajectories-visibilitat.md).

---

## 9. 🌌 El Cel: Traces Estel·lars i Exposició Temporal (Star Trails)

### 9.1. Què fa i per a què serveix

Simula captures fotogràfiques de molt llarga exposició, acumulant de forma progressiva les traces circulars que descriuen les estrelles al voltant del pol celeste a mesura que la Terra gira.

### 9.2. Com s'utilitza

1. A la pestanya **🌌 Cel**, obriu la secció **Traces estel·lars (Star Trails)**.
2. Premeu **Iniciar exposició** i avanceu el temps de simulació. La càmera s'orientarà automàticament cap al pol celeste (Polaris a l'hemisferi nord) i començarà a dibuixar els arcs lluminosos continus.
3. Premeu **Pausa** per aturar la captura o **Reiniciar** per netejar el buffer.

### 9.3. Com funciona per dins

El mòdul acumula a la GPU segments de línia obtinguts per la integració de la velocitat angular sideral de la Terra:
$$\omega_{\text{sideral}} = \frac{2\pi}{86164.0905\text{ s}} \approx 7.292115 \times 10^{-5}\text{ rad/s}$$
mantenint un nombre fitat de recursos de GPU mitjançant buffers circulars retinguts.

**Passos d'origen:** [Pas 14 — Traces circumpolars](tasques/completat/pas14.md).

---

## 10. ⛰️ Terra: Relleu DEM 3D, Horitzó Real Calculat i Cobertura de Superfície

### 10.1. Què fa i per a què serveix

Reconstrueix la topografia tridimensional del paisatge al voltant de l'observador a partir de models digitals d'elevació (DEM), calcula la silueta d'horitzó real a 360° tenint en compte la curvatura de la Terra i la refracció atmosfèrica, i aplica textures categòriques de Land Cover amb identificació en passar el ratolí.

### 10.2. Com s'utilitza

- A la pestanya **⛰️ Terra (Topografia)**:
  - Activeu **Horitzó real** per calcular l'oclusió sobre les muntanyes.
  - Activeu **Cobertura de superfície** per visualitzar boscos, conreus, masses d'aigua i zones urbanes.
  - Feu clic a qualsevol punt de la muntanya per activar el vol ràpid **GoTo** cap a aquella coordenada.
  - Passeu el ratolí sobre el relleu per veure el tipus de cobertura vegetal en una etiqueta emergent.

### 10.3. Com funciona per dins: Càlcul de l'Horitzó Angular Topogràfic

L'altitud de l'horitzó angular des de la posició de l'observador a alçada $h_0$ a una distància $d$ sobre la cota $h(d)$ s'avalua considerant la curvatura terrestre i la refracció atmosfèrica mitjançant el **Radi Terrestre Efectiu** $R_{\text{eff}} = \frac{4}{3} R_{\text{Terra}} \approx 8495\text{ km}$:
$$\theta_{\text{hor}}(\text{az}) = \max_{d \in [0, d_{\max}]} \left[ \arctan\left( \frac{h(d, \text{az}) - h_0 - \frac{d^2}{2 R_{\text{eff}}}}{d} \right) \right]$$

**Passos d'origen:** [Pas 15 — Elevació i horitzó](tasques/completat/pas15.md), [Pas 16 — Terreny 3D retingut](tasques/completat/pas16.md), [Pas 17 — Superfície categòrica](tasques/completat/pas17-superficie-progressiva.md).

---

## 11. 📐 Eines: Modes d'Observació Instrumental (Òptica i Fotografia)

### 11.1. Què fa i per a què serveix

Permet simular la visió a través d'instruments òptics reals: ull humà natural (*Naked Eye*), càmeres fotogràfiques amb diferents formats de sensor i distàncies focals, i telescopis astronòmics amb oculars intercanviables.

| Ull nu (*Naked Eye*) | Càmera fotogràfica (*Camera*) | Telescopi (*Scope*) |
| :---: | :---: | :---: |
| ![Ull nu](evidencies/pas19/eye.png) | ![Càmera](evidencies/pas19/camera.png) | ![Telescopi](evidencies/pas19/telescope.png) |
| *Visió humana natural a 360°.* | *Simulació de sensor (Full Frame, APS-C) i focal.* | *Reticle circular d'ocular i magnificació.* |

### 11.2. Com s'utilitza

1. A la pestanya **📐 Eines**, trieu el mode d'observació desitjat:
   - **Mode Càmera:** Seleccioneu la mida del sensor (*Full Frame 35mm*, *APS-C*, *Micro 4/3*, *1"*) i la distància focal de l'objectiu ($14\text{ mm} - 600\text{ mm}$). La cúpula mostrarà el marc de composició amb el camp de visió exacte.
   - **Mode Telescopi:** Definiu la distància focal del tub òptic i de l'ocular per calcular el cercle de camp i l'augment.

### 11.3. Com funciona per dins: Òptica Geomètrica

El camp de visió horitzontal ($\text{FOV}_{\text{h}}$) i vertical ($\text{FOV}_{\text{v}}$) d'un sensor de dimensions $w_{\text{sensor}} \times h_{\text{sensor}}$ i distància focal $f$ es calcula com:
$$\text{FOV}_{\text{h}} = 2 \arctan\left( \frac{w_{\text{sensor}}}{2 f} \right), \quad \text{FOV}_{\text{v}} = 2 \arctan\left( \frac{h_{\text{sensor}}}{2 f} \right)$$
La magnificació telescòpica s'obté com $M = \frac{f_{\text{telescopi}}}{f_{\text{ocular}}}$.

**Passos d'origen:** [Pas 19 — Modes d'observació instrumental](tasques/completat/pas19-modes-optics.md).

---

## 12. 📐 Eines: Instruments de Mesura Esfèrica

### 12.1. Què fa i per a què serveix

Permet traçar instruments de mesura directa sobre l'esfera celeste: regles de distància angular (cercle màxim), cercles esfèrics, quadrats i rectangles orientats, amb càlcul rigorós de distàncies en graus, minuts i segons ($^\circ \ ' \ ''$) i àrees en graus quadrats ($\text{deg}^2$) o estereoradiants ($\text{sr}$).

![Quatre eines de mesura esfèrica desplegades](evidencies/pas21/four-tools.png)

### 12.2. Com s'utilitza

1. Aneu a la pestanya **📐 Eines** i trieu una eina: **Regla**, **Cercle**, **Quadrat** o **Rectangle**.
2. Feu clic i arrossegueu sobre la cúpula 3D per traçar la figura.
3. Utilitzeu les nanses de vora per redimensionar o rotar la mesura.
4. Desfeu o torneu a aplicar canvis amb `Ctrl+Z` / `Ctrl+Y` o mitjançant els botons de la interfície:

![Edició, eliminació i historial desfer](evidencies/pas21/edit-delete-undo.png)

### 12.3. Com funciona per dins: Geometria Esfèrica i Fórmula del Semiversin

La separació angular $\Delta \sigma$ entre dos punts $(\alpha_1, \delta_1)$ i $(\alpha_2, \delta_2)$ es resol mitjançant la **fórmula del semiversin** (*haversine*), immune a errors d'arrodoniment en angles petits:
$$\text{hav}(\Delta \sigma) = \sin^2\left(\frac{\delta_2 - \delta_1}{2}\right) + \cos \delta_1 \cos \delta_2 \sin^2\left(\frac{\alpha_2 - \alpha_1}{2}\right)$$
$$\Delta \sigma = 2 \arcsin\left(\sqrt{\text{hav}(\Delta \sigma)}\right)$$
L'àrea d'un polígon esfèric de $n$ vèrtexs amb angles interiors $\theta_i$ es calcula a partir de l'**excés esfèric de Girard ($E$)**:
$$E = \left( \sum_{i=1}^n \theta_i \right) - (n - 2)\pi \quad [\text{sr}], \quad \text{Àrea} = E \cdot \left(\frac{180}{\pi}\right)^2 \quad [\text{deg}^2]$$

**Passos d'origen:** [Pas 21 — Eines de mesura esfèrica](tasques/completat/pas21-eines-mesura.md).

---

## 13. 🌌 Constel·lacions de referència i figures pròpies

### 13.1. Cerca i observació

El cercador reconeix el nom llatí i l'abreviatura de cadascuna de les 88 constel·lacions IAU. En seleccionar-ne una, TerraLab3D mostra la figura visual adoptada, centra el seu centre calculat sobre aquest traçat i permet aplicar-hi el seguiment i la trajectòria del cel com a qualsevol altre objectiu equatorial fix.

Les línies visibles són un **traçat visual de referència**, no fronteres ni línies oficials de la IAU. El centre i el radi d'enquadrament també descriuen aquest traçat. En el cas de Serpens, Caput i Cauda pertanyen a una única constel·lació però es mantenen com dos components desconnectats.

### 13.2. Edició de figures pròpies

1. Aneu a **📐 Eines → Constel·lacions** i creeu o seleccioneu un grup.
2. Activeu **Editar** i feu clic prop d'una estrella visible; la candidata ha d'estar a un màxim de 16 píxels.
3. Useu **Traç nou** per començar un component discontinu, i **Finalitzar** per sortir de l'edició.
4. Podeu reanomenar, eliminar, desfer i refer durant la sessió. El document es desa entre reinicis, però l'historial de desfer/refer no.
5. **Mostrar totes** només canvia la visibilitat del catàleg i no modifica les figures pròpies.

| Constel·lació personalitzada sencera aïllada | Catàleg oficial de constel·lacions (Zoom-out complet) |
| :---: | :---: |
| ![Constel·lació personalitzada sencera](evidencies/pas23/edicio-i-visibilitat.png) | ![Catàleg de constel·lacions en zoom-out](evidencies/pas23/constellacio-amb-trajectoria.png) |
| *Figura pròpia («Triangle d'Estiu propi») en verd maragda (`#6ee7a8`) visualitzada sencera i amb marges confortables sobre la Via Làctia, sense altres constel·lacions actives.* | *Panoràmica de la volta celeste en zoom-out màxim (FOV 115°) mostrant la xarxa de constel·lacions de referència en blanc (Cygnus, Aquila, Pegasus, Sagittarius, Hercules...) sense constel·lacions d'usuari.* |

El traçat de referència deriva de d3-celestial sota BSD-3-Clause. L'avís complet, el commit i els fitxers d'origen consten a [THIRD-PARTY.md](../THIRD-PARTY.md).

**Pas d'origen:** [Pas 23 — Constel·lacions](tasques/completat/pas23-constellacions.md).

---

## Apèndix A — Taula de Dreceres de Teclat i Gestos Ràpids

| Tecla / Gest | Acció | Context operatiu |
| :--- | :--- | :--- |
| `Esc` | Allibera seguiment de càmera / Tanca diàlegs / Retorna a Ull nu | Global |
| `W`, `A`, `S`, `D` | Desplaçament de càmera endavant, esquerra, enrere, dreta | Mode Caminar / Avió |
| `F` | Intercanvi entre mode caminar i mode avió | Mode Caminar / Avió |
| `Espai` | Pausa / Reprèn el rellotge de simulació temporal | Global |
| `Ctrl + Z` | Desfer la darrera mesura o edició | Eines de mesura |
| `Ctrl + Y` / `Ctrl + Shift + Z` | Refer la darrera mesura desfeta | Eines de mesura |
| `Supr` / `Delete` | Elimina la mesura esfèrica seleccionada | Eines de mesura |
| `Roda del ratolí` | Zoom / Variació contínua del camp visual ($\text{FOV}$) | Global |
| `Clic esquerre` | Selecció d'astres, identificació Gaia o punts DEM | Global |

---

## Apèndix B — Oracles de Càlcul Científic, Fonts de Dades i Toleràncies

| Mòdul | Font de dades científica / Oracle | Tolerància de validació |
| :--- | :--- | :--- |
| **Temps i Sideral** | IAU SOFA / IERS Conventions (GMST, LST) | $\le 10^{-6}\text{ s}$ d'error temporal |
| **Efemèrides Planetàries** | JPL DE440 / SPICE kernels | $\le 0.05''$ d'arc topocèntric |
| **Catàleg Estel·lar** | ESA Gaia DR3 / Hipparcos fallback | $\le 0.01''$ d'arc en posicions J2000 |
| **Superfície Lunar** | NASA LRO/LOLA 8K albedo & topography | Precisió d'albedo 8-bit, libració $< 0.01^\circ$ |
| **Topografia i Elevació** | Models Digitals d'Elevació (DEM) locals | Interpolació bilineal sub-mètrica |
| **Òptica i Mesures** | Fórmules analítiques de cercle màxim i Girard | $\le 10^{-5}\text{ deg}$ d'error angular |

---

## Apèndix C — Preguntes Freqüents i Resolució d'Incidències (FAQ)

### Com puc seguir un planeta o la Lluna mentre avança el temps ràpidament?

Feu clic sobre el cos celeste o cerqueu-lo al cercador de la pestanya **Cel**. El sistema activarà immediatament el seguiment de càmera (`Seguint ✓` al HUD daurat), mantenint el cos centrat durant l'avanç temporal.

### Per què la línia de trajectòria es veu discontínua i lila?

La línia discontínua lila indica que en aquell tram l'astre està ocult darrere de les muntanyes del relleu local o sota l'horitzó. El traç es manté visible perquè pugueu anticipar exactament per on i a quina hora sortirà o es pondrà l'astre.

### Com puc saber l'hora exacta de posta de sol darrere una muntanya?

Seleccioneu el Sol i activeu la casella *Trajectòria de l'objecte*. A la cúpula 3D apareixerà una targeta compacta anomenada `↓ Posta` amb l'hora exacta del creuament del disc solar amb la carena de la muntanya.

### Com puc comprovar com es veurà una constel·lació amb la meva càmera i objectiu?

Aneu a la pestanya **Eines**, seleccioneu el mode **Càmera**, trieu el vostre sensor (ex: *Full Frame 35mm*) i la focal que voleu utilitzar (ex: *50 mm*). La pantalla mostrarà el marc de composició exacte que obtindreu a la vostra fotografia.

---

> **TerraLab3D** — Desenvolupat amb rigor científic i tecnologies web d'última generació.


## Contaminació lumínica: configuració espectral realista i per kelvins

Implementat a [7.5.1](tasques/completat/pas7.5.1-black-marble-spectral-simulation.md). Obriu el calaix **Cel** i desplaceu-vos a **Contaminació lumínica**. El selector principal ofereix «Simulació realista» i «Simulació per kelvins». El model visual històric de Bortle/magnitud conserva els controls identificats a sota.

En mode Kelvin, l’etiqueta superior **Temperatura de color** mostra el valor actual. El lliscant horitzontal té **2.800 K a l’esquerra** i **6.500 K a la dreta**, amb etiqueta inferior **«Exemple: ...»**. S’ajusta amb ratolí, tacte i teclat (fletxes, Inici i Fi). El text d’exemple és orientatiu i no canvia la tecnologia: la família estable és LED de fòsfor CIE B1–B5, amb la font de dades visible. El domini 1.800–2.800 K encara no està cobert per aquesta família i no s’extrapola.

![Control de kelvins, escala i exemple dins del panell Cel](evidencies/pas7.5.1/control-kelvins.png)

La normalització permet conservar flux lluminós fotòpic, potència radiant, resposta DNB de referència o escala relativa. Python calcula una SPD interpolada i la seva CCT efectiva. Aquest valor no és una temperatura urbana mesurada ni una garantia de tolerància de fabricació.

En **Simulació realista**, el model considera un ensemble determinista de mescles espectrals hipotètiques amb pesos de flux radiant; no dedueix els kelvins de la ciutat d’una banda DNB. La connexió local al grànul NOAA-20 real genera fonts relatives amb QA i procedència. L’adquisició ordinària geogràfica arribarà pel gestor comú del Pas 24.

![Selector de simulació realista i estat del transport](evidencies/pas7.5.1/simulacio-realista.png)

La UI indica **transport atmosfèric pendent**: els controls configuren fonts científiques, però encara no alteren físicament el cel ni mostren una brillantor atmosfèrica calculada. La visualització física continua obligatòria a 7.25–7.27; no es fa servir un filtre RGB per representar aquest resultat.

## SG-REF: càlcul de referència offline

Implementat al [Pas 7.6](tasques/completat/pas7.6-sg-ref-reference-solver.md). Amb el backend i les dependències instal·lats, executeu des de l’arrel:

```powershell
python -X utf8 tools/run_sg_ref_step7_6.py --output .runtime-sgref-resultats.json
```

El CLI calcula fixtures analítiques, un rectangle i el raster equivalent, 401 longituds d’ona CIE, refinaments de fase i nou contrasts de dispersió múltiple. El fitxer només es reemplaça quan tots els contrasts han acabat. Ctrl+C cancel·la el treball; una fallada de convergència provoca sortida no nul·la i no publica un resultat parcial.

Per reproduir també les 18 alternatives C del píxel NOAA-20 real verificat, afegiu `--with-real-black-marble`. `--data-root I:\TerraLab` permet indicar l’arrel dels assets instal·lats; sense aquesta opció s’utilitza la configuració de dades de l’aplicació. Calen el grànul i el manifest RSR exactes documentats a l’[informe](evidencies/pas7.6/validacio-sg-ref.md); el CLI no els descarrega ni substitueix. Els perfils cosinus tabulats poden requerir desenes de milers d’avaluacions LOS: aquesta eina és offline.

Al JSON, `referenceRadiance.values` conté radiància espectral per direcció; `unit` diferencia watts de l’escala relativa C. `refinement_history`, `numerical_error_estimate`, `input_signature`, revisions i context de font permeten reproduir el càlcul. Cada alternativa C té el seu resultat: no se sumen les sis hipòtesis d’un mateix píxel.

La referència actual usa un pla local amb atmosfera espectral homogènia, terra negre i cel clar escalar. L’error estimat de quadratura no és un interval garantit ni la incertesa urbana. F5 afegeix error mostral i cota de la cua d’ordres múltiples dels seus benchmarks. Terreny, curvatura, atmosfera real, validació H i connexió a la UI continuen als passos posteriors. [Resultats verificats](evidencies/pas7.6/resultats-sg-ref-v1.json).

![Convergència de fase i biaix de dispersió múltiple en els benchmarks SG-REF](evidencies/pas7.6/convergencia-i-biaix-f5.png)

## B0: geometria del kernel i benchmark

El [Pas 7.7](tasques/completat/pas7.7-kernel-geometry-b0.md) és una eina CPU de diagnòstic. Des de l’arrel, amb el backend instal·lat:

```powershell
python -X utf8 tools/benchmark_skyglow_b0.py --output-dir .runtime-b0-resultats
```

La figura es pot regenerar amb `tools/plot_skyglow_b0.py --input <resultats-b0-v1.json> --output <figura.png>`; aquesta eina auxiliar requereix matplotlib opcional.

La consola mostra cinc warm-ups i trenta passades mesurades per cada mida de fonts. La sortida inclou `resultats-b0-v1.json` amb maquinari, versions, fixtures, signatures, agregats i exemples de LOS, i `passades-b0-v1.csv` amb les 180 mesures individuals. `runId`/`run_id` permeten relacionar els dos fitxers. Ctrl+C cancel·la la campanya; els fitxers finals se substitueixen després del càlcul, sense publicar un resultat parcial com a vàlid.

L’integrand és 1 i el resultat són metres de trajecte. El zenit passa pel mateix operador i les mateixes regles GK7/15 que les altres elevacions. La geometria és una esfera explícita, amb ENU local i cel·les geomètriques: no és un model atmosfèric o DEM. Els temps són una línia base del maquinari mesurat, no un SLO de producte. La UI i el cel físic encara no reben radiància d’aquest kernel. [Resultats i límits](evidencies/pas7.7/validacio-b0.md).

![Escalat i distribució de latència del benchmark geomètric B0](evidencies/pas7.7/escalat-i-latencia-b0.png)

## Camp òptic estàndard: perfils i travesses multi-tile

El [Pas 7.8](tasques/completat/pas7.8-optical-field-standard.md) ofereix un diagnòstic CPU offline. Des de l’arrel, amb el backend instal·lat:

```powershell
python -X utf8 tools/validate_optical_field_step7_8.py --output .runtime-optical/resultats.json
python -X utf8 tools/plot_optical_field_step7_8.py --input .runtime-optical/resultats.json --output .runtime-optical/perfils.png
```

La segona ordre requereix matplotlib opcional. La consola informa de les columnes amb 1, 2 i 8 tiles i una fixture de contrast lateral; el JSON conserva els perfils P/T, procedències, instants, bounds ENU fixos, versions, segments i dependències realment utilitzades. `integral_unit=m^-2` indica columna molecular ∫n ds; `stage=optical_field_column_diagnostic_not_radiance` indica el domini del resultat. El fitxer final es reemplaça després de tots els controls; una fallada o Ctrl+C no publica un resultat parcial vàlid.

El model és COESA 1975, NASA TR R-459 publicat el 1976, sec i limitat a 0–50 km. El perfil per defecte usa nusos cada 100 m, log(P) i T lineals, i densitat derivada del gas ideal. Les fixtures cobreixen fins a 10 km; no són meteorologia observada. La figura mostra l’error d’interpolació separat de la quadratura. La consulta fora de cobertura falla, sense extrapolació. Aerosols, absorció gasosa i núvols continuen absents; la dispersió arribarà a 7.9. La UI encara no rep radiància d’aquest kernel. [Resultats i límits](evidencies/pas7.8/validacio-optical-field.md).

![Perfils del camp atmosfèric sec i convergència vertical](evidencies/pas7.8/perfils-i-convergencia.png)

## B1: radiància monocromàtica de dispersió simple

El [Pas 7.9](tasques/completat/pas7.9-rayleigh-aerosol-b1.md) permet executar la física de Rayleigh/aerosol offline:

```powershell
python -X utf8 tools/benchmark_skyglow_b1.py --output-dir .runtime-b1-resultats
python -X utf8 tools/plot_skyglow_b1.py --input .runtime-b1-resultats/resultats-b1-v1.json --output-dir .runtime-b1-resultats
```

La consola mostra set diagnòstics, cinc escalfaments i les passades mesurades; la ruta directa pot trigar força. `--diagnostics-only` omet la campanya temporal. El JSON conté fonts, medi, banda/fases, procedències, signatures de codi/entrades, residuals SG-REF i agregats. El CSV conserva cada passada amb `run_id`, temps, RSS i comptadors de LOS, fase i transmissió. Una fallada o Ctrl+C no substitueix els fitxers finals amb dades parcials. Les figures requereixen matplotlib opcional.

`stage=single_scattering_monochromatic_B1` identifica el resultat a 550 nm; `integral_unit` diferencia W m⁻² sr⁻¹ nm⁻¹ d’una escala relativa C. El model no inclou absorció gasosa, núvols ni visibilitat física de terreny. La fixture homogènia i l’aerosol HG són prescrits; no representen meteorologia mesurada. El rectangle es calcula per àrea i el zenit usa el mateix kernel que les altres elevacions. La UI continua amb transport físic pendent de connexió a 7.25–7.27.

![Refinament de fase i residuals de B1, sense gate radiomètric](evidencies/pas7.9/fase-i-residuals-b1.png)

![Escalat i latència mesurats del B1 directe](evidencies/pas7.9/escalat-i-latencia-b1.png)

Els temps són observacions d’aquest maquinari, sense SLO de producte. El residual contra SG-REF és diagnòstic; el gate radiomètric és 7.12 i l’homologació urbana H continua pendent. [Resultats i límits](evidencies/pas7.9/validacio-b1.md).

## Transport espectral i diagnòstic de gasos B2/B4

El [Pas 7.10](tasques/completat/pas7.10-gas-spectral-kernel.md) ofereix transport espectral offline amb fonts S/C. Amb el backend instal·lat, executeu des de l'arrel i useu una carpeta nova per preservar les evidències congelades:

```powershell
python tools/benchmark_skyglow_spectral.py --output .runtime-espectral-local
python tools/validate_spectral_transport_step7_10.py --output .runtime-espectral-local
python tools/validate_gas_bands_step7_10.py --output .runtime-espectral-local
python tools/diagnose_spectral_transport_step7_10.py --output .runtime-espectral-local
python tools/plot_spectral_transport_step7_10.py --root .runtime-espectral-local
```

La campanya principal de 900 LOS va durar aproximadament vint minuts en el maquinari verificat. Els JSON/CSV inclouen temps, comptadors, identitats i unitats. Schema 4 diferencia B2 (gasos desactivats explícitament per diagnosi) i B4 (composició prescrita). La radiància integrada té unitat W m⁻² sr⁻¹ o escala relativa C; el pes CIE d'aquest diagnòstic no és encara una projecció SQM/TESS ni una acreditació de lúmens urbans.

La LUT empaquetada només acredita O3 entre 380–780 nm i 203–293 K. La composició i els perfils són explícits; cobertura o espècies absents fallen i no s'extrapolen. No acredita H2O/O2/NO2, aire terrestre complet, meteorologia real ni H. La modalitat per kelvins conserva les SPD CIE i les normalitzacions de 7.5.1, però la radiància encara no arriba al renderer.

![Cost mesurat per etapa i latència B0/B1/B2/B4](evidencies/pas7.10/cost-etapes-i-latencia.png)

![Pressupost espectral de 0,01 mag revalidat](evidencies/pas7.10/pressupost-espectral.png)

![Efecte del sostre 10–50 km segons medi i elevació](evidencies/pas7.10/sensibilitat-sostre-atmosferic.png)

Al zenit de la fixture B4 estàndard, un sostre de 10 km dona 22,45% menys radiància que 50 km. A7.10, la cua superior a50km restava desconeguda: el control del sostre no és una estimació de l'error espectral ni una qualificació física universal. Els temps de perfils variables es documenten separadament de la fixture homogènia de 900 LOS. [Resultats, procedència i límits](evidencies/pas7.10/validacio-espectral-i-gasos.md). L'ampliació de terreny de 7.11 es descriu a continuació; el gate posterior7.12 es descriu a continuació.

### Terreny opac del transport offline — Pas 7.11

El [Pas 7.11](tasques/completat/pas7.11-terrain-curvature.md) amplia la mateixa ruta directa B0/B1/B2/B4. No afegeix controls ni radiància física a la pantalla de producte. Per inspeccionar fixtures i radiàncies:

```powershell
python -X utf8 tools/validate_terrain_step7_11.py --output .runtime-terreny-local --part topology
python -X utf8 tools/validate_terrain_step7_11.py --output .runtime-terreny-local --part transport
python -X utf8 tools/validate_terrain_step7_11.py --output .runtime-terreny-local --part area
python -X utf8 tools/validate_terrain_step7_11.py --output .runtime-terreny-local --part dem
```

La muntanya trunca el raig de l'observador i oculta contribucions de font, amb salts binaris explícits. Un rectangle parcialment ocult integra només l'àrea visible: no es fa transparent la muntanya ni es multiplica una font puntual per un alfa. Els escenaris C realista/K conserven SPD i escala relativa, amb geometria traslladada expressament a la fixture sintètica.

![Topologia, salt de visibilitat i curvatura](evidencies/pas7.11/topologia-i-visibilitat.png)

El constructor consumeix l'adaptador DEM existent, exigeix convenció/conversió d'altures i límit superior del model, i rebutja nodata i cobertura insuficient. La graella triada és explícita i té pressupost de vèrtexs; no s'afina automàticament. La demostració amb el DEM real de 5 m empra nou nusos i no certifica una conversió geoidal ni representa tot el detall del raster. Per reproduir-la cal la biblioteca configurada; la instantània i els hashes es conserven a les evidències.

![Cost d'oclusió mesurat, sense acceleracions posteriors](evidencies/pas7.11/cost-oclusio.png)

Les fonts extenses amb retall directe són costoses; els ordres alts són eines de diagnòstic. Els resultats de 90 LOS no s'extrapolen a la campanya històrica de 900 LOS. **El sostre de 10 km continua ometent 22,45% respecte a 50 km en el zenit B4 de 7.10**; en aquell tancament, la cua superior encara era desconeguda. [Informe i límits](evidencies/pas7.11/validacio-terreny-i-visibilitat.md). El gate posterior7.12 es descriu a continuació.


### Gate radiomètric offline — Pas 7.12

El gate separa el transport donat un camp discret de la credibilitat física d'aquest camp. Les fixtures S defineixen potència d'1W; B1 conserva l'espectre pla històric a550nm i B4 usa LED-B3 integrada amb resposta CIE V. Les fonts C realista/K conserven escala relativa i no es converteixen en observacions validades. La instantània DEM arxivada es reprodueix sense accés al raster original; la seva convenció d'altura continua sent explícita.

Per reproduir la campanya, escolliu una carpeta nova i preserveu els resultats:

```powershell
python -X utf8 tools/validate_transport_gate_step7_12.py --output .runtime-gate-local/campanya-v1 --part bind
python -X utf8 tools/validate_transport_gate_step7_12.py --output .runtime-gate-local/campanya-v1 --part gate
python -X utf8 tools/validate_transport_gate_step7_12.py --output .runtime-gate-local/campanya-v1 --part ceiling
python -X utf8 tools/diagnose_transport_gate_step7_12.py --output .runtime-gate-local --part errors
python -X utf8 tools/diagnose_transport_gate_step7_12.py --output .runtime-gate-local --part compatibility
python -X utf8 tools/bound_lut_transport_gate_step7_12.py --output .runtime-gate-local/cota-lut-refinada-i-pressupost.json
python -X utf8 tools/audit_transport_gate_step7_12.py --root .runtime-gate-local --part tail
```

La reproducció completa requereix temps: fonts extenses amb terreny i columnes variables són especialment costoses. `gate` i `ceiling` reprenen les files ja persistides només si el codi coincideix amb la vinculació. El criteri congelat es llegeix del repositori; no s'edita segons el residual obtingut. Els JSON guarden PASS/FAIL per cas i no acrediten peticions arbitràries del kernel. Els resultats crus anteriors conserven els esquemes i marcadors històrics de compatibilitat; el veredicte nou pertany a l'informe de validació.

L'ampliació COESA fins a75km és optativa. La contribució superior s'acota positivament sota les hipòtesis d'aire sec hidrostàtic i aerosol prescrit, sense posar-la a zero ni exigir P(infinit)=0. [Domini i derivació](evidencies/pas7.12/domini-i-cota-exterior.md). Les incerteses de composició real, dispersió múltiple, inferència urbana i datum DEM continuen separades. En aquell tancament7.13 encara no s'havia iniciat.

[Resultat verificat de7.12](evidencies/pas7.12/validacio-gate-transport.md):9 fixtures S PASS,42 sostres i444 proves. La cota exterior màxima és0,000472296mag; validesa condicionada al model prescrit, sense homologació observacional.

![Gate numèric i domini vertical](evidencies/pas7.12/gate-i-convergencia-vertical.png)

![Cost actual del transport i l'oclusió](evidencies/pas7.12/cost-transport-i-oclusio.png)

L'auditoria final de la campanya arxivada s'executa amb python tools/audit_transport_gate_step7_12.py --root docs/evidencies/pas7.12 --part final. Una campanya nova necessita també regenerar les regressions i els seus manifests; el CLI final retorna error si falten fitxers o falla el criteri. Les primeres/repeticions de rendiment s'obtenen amb diagnose_transport_gate_step7_12.py --part benchmark; els estimadors complets, amb --part diagnostics, i els controls separats d'oracle, amb --part oracle-controls (sempre amb --output). No s'extrapola una font extensa a900LOS ni es declara SLO. En aquell tancament7.13 encara no s’havia iniciat.

### Diagnòstic científic angular — Pas 7.13 adaptatiu

La [capacitat offline](tasques/completat/pas7.13-dome-profile-direct.md) genera mapes d’azimut/elevació amb escala logarítmica, unitats i procedència. El [candidat v1 fallit](evidencies/pas7.13/validacio-camp-angular.md) es conserva com a evidència històrica; la v2 utilitza mostreig adaptatiu i validació independent.

![Mapa adaptatiu S/C realista i kelvins](evidencies/pas7.13/adaptatiu-v2/mapa-calor-adaptatiu-v2.png)

Els dos escenaris C comparteixen escala relativa i mantenen la normalització original. No comparis aquestes unitats amb watts de S o mesures urbanes: S és una font d’1 W definida; C conserva dades/SPD de 7.5.1 amb geometria puntual sintètica traslladada. La figura és una cambra homogènia finita de 75 km, no atmosfera COESA ni cel observat de Barcelona. El rètol PASS es refereix als holdouts i al domini registrats, no al renderer de l’aplicació ni a qualsevol altra ciutat.

![Diferència relativa realista/kelvins](evidencies/pas7.13/adaptatiu-v2/diferencia-realista-kelvins.png)

A normalització conservada, 3.000 K dona entre un 1,44% i un 2,01% més que realista en la graella diagnòstica. És una diferència entre hipòtesis espectrals C, sense calibratge absolut. La graella de presentació només reconstrueix dades: els píxels no són noves mesures independents.

El [gate](evidencies/pas7.13/adaptatiu-v2/gate-adaptatiu-v2.json) verifica 900 holdouts de cambra amb màxim 0,001894297 mag i tres de perfil COESA amb 0,004964471 mag, davant 0,01 mag. COESA conserva perfil d’1 km, sostre de 75 km i cota exterior positiva condicionada; el perfil només està contrastat a azimut 270,7° i elevacions 45–60°. No hereta una homologació de tota la semiesfera. Es preserva la limitació històrica de 10 km i el 22,45% omès a B4 de 7.10.

![Control de reconstrucció COESA i llindar](evidencies/pas7.13/adaptatiu-v2/perfil-coesa-i-error.png)

Amb el checkout i les representacions binàries del candidat original, `python -X utf8 tools/audit_adaptive_dome_step7_13_v2.py` reprodueix l’auditoria arxivada; els seus hashes estrictes no corresponen al kernel ampliat de 7.14. Des de l’arrel, l’auditoria actual és `python -X utf8 tools/audit_photometry_step7_14.py --numeric-only` i `python -X utf8 tools/plot_adaptive_dome_step7_13_v2.py` regenera les sis figures sense executar noves integrals. `tools/audit_regressions_step7_13_v2.py` compara B0, les quatre columnes i els baselines. El CLI v1 `audit_angular_step7_13.py --strict` continua retornant 1 pel FAIL històric.

El nou cas d’ús és `terralab3d.application.adaptive_dome_sampling.sample_adaptive_dome(request)`: rep sostre i precisions de la petició i retorna un camp cru amb procedència/revisió; no concedeix PASS a entrades arbitràries. Rebutja DEM i àrees sense domini angular acreditat. Per a aquestes geometries, barreres i zeros sense garanties, executa LOS directes amb el kernel existent o mostra dada no disponible. `None/null` no significa zero ni transparència; cobertura absent és error. En camps amb barreres azimutals, l’ús acreditat és `directOnly=true`.

La campanya ha costat 76,35 min. Cada camp ha necessitat 7.736 LOS i conserva 54 perfils/717 nusos. Els controls COESA nous costen uns 173–179 s per LOS de kernel; es preserven els aproximadament 609 s/LOS extensa de 7.12. Abans d’ampliar la campanya, estima el cost i preregistra el domini. No hi ha cache entre peticions, acceleració espacial, vectorització addicional o multicore. En aquell tancament 7.14 i Three.js definitiu encara no s’havien iniciat.

### Projeccions fotomètriques offline — Pas 7.14 parcial

La [capacitat verificada](tasques/pendent/pas7.14-photometric-projections.md) projecta dades espectrals retingudes, amb zero avaluacions noves de transport. La lectura CIE de S és luminància modelada del component artificial en cd/m²; C continua relatiu. Les bandes SQM/TESS de referència no són lectures d’un instrument calibrat i la sortida nativa indica `unavailable` amb la causa. Bortle no es dedueix d’aquests resultats.

![Suport de les respostes fotomètriques](evidencies/pas7.14/respostes-i-suport.png)

Des de l’arrel, per inspeccionar el cas S arxivat sense executar transport:

```powershell
python -X utf8 tools/project_skyglow_photometry.py --input docs/evidencies/pas7.14/transport-i-projeccions.json --case S_B4_chamber_point_5km-0 --reference-bands --output .runtime-photometry/projeccio-usuari.json
```

La sortida ha de ser nova. Conté senyals de banda, unitats, escala, resposta, revisió i motiu d’indisponibilitat. `--reference-bands` afegeix diagnòstics AB direccionals condicionats, sense aplicar un FOV ni un zero point natiu. [Exemple executat](evidencies/pas7.14/demostracio-cli-s.json). Les magnituds C absolutes continuen indisponibles.

![Luminància S, contrast C i cost](evidencies/pas7.14/escenaris-i-costos.png)

El [gate numèric](evidencies/pas7.14/gate-projeccions-v1.json) es reprodueix amb `python -X utf8 tools/audit_photometry_step7_14.py --numeric-only`; sense l’opció retorna 1 perquè el pas científic complet està bloquejat. `python -X utf8 tools/plot_photometry_step7_14.py` regenera les tres figures amb les dades arxivades. No genera una malla nova.

La projecció de les bandes costa 3,06–5,11 ms/LOS; la captura COESA registrada costa 183,393 s. No és una acceleració del transport. L’espectral passa 10.624 contrasts amb màxim 0,000115197 mag davant 0,01, dins finestres conegudes. Una lectura nativa necessita resposta/fosc/FOV/calibratge coherents. Un model nominal AB no exigeix calibratge individual, però necessita resposta i cobertura suficients. El DomeProfile CIE i el domini angular de 7.13 no cobreixen aquests requisits: no s’extrapola COESA, DEM o fonts extenses ni es renormalitza una regió parcial. La contribució superior a 75 km es conserva com a cota positiva condicionada; 10 km continua insuficient a la fixture històrica B4. El punt de represa segueix a 7.14; 7.15 no iniciat.

### CIE amb aire/buit explícit i perfils nominals — represa7.14

La [represa](evidencies/pas7.14/represa-v2/validacio-represa-v2.md) incorpora una projecció CIE2019 versionada: V està en aire estàndard450ppm i les dades retingudes es declaren en buit. El canvi conserva flux quan es converteix una densitat; no canvia la SPD d’un transport anterior ni el seu resultat històric. Aquesta operació és un postprocessament independent, sense noves LOS.

```powershell
python -X utf8 tools/project_coordinate_photometry_step7_14_v2.py --input docs/evidencies/pas7.14/transport-i-projeccions.json --case S_B4_chamber_point_5km-0 --input-radiance-basis vacuum_nm --output .runtime-photometry-v2/projeccio-usuari.json
```

La sortida ha de ser nova. Mostra senyal de banda, luminància S en cd/m² o senyal C relatiu, coordenades i refinament numèric. [Exemple executat](evidencies/pas7.14/represa-v2/demostracio-cli-cie-v2.json). No produeix lectura SQM/TESS nativa ni Bortle. El postprocessament exacte de coordenades costa0,787–0,888s/LOS en la campanya; no se li atribueixen els3–5ms del projector lineal anterior.

![Canvi explícit de coordenada en les ponderacions S/C](evidencies/pas7.14/represa-v2/canvi-coordenades-cie-v2.png)

Un model nominal verificable pot definir una banda AB sense conèixer el fosc o el guany d’un dispositiu concret. Per comparar amb Hz o magnituds natives calen aquelles dades addicionals. Les [fonts primàries i límits](evidencies/pas7.14/represa-v2/fonts-i-qualificacio-v2.md) distingeixen SQM ample de SQM-L i lots TESS-W; no hi ha un perfil genèric acreditat només pel nom comercial. La cobertura espectral/angular completa o les cotes pertinents continuen pendents.

`python -X utf8 tools/audit_photometry_resume.py --numeric-only` reprodueix el PASS numèric. Sense l’opció retorna1 pel gate científic bloquejat. `python -X utf8 tools/plot_photometry_resume.py` regenera les tres figures sense repetir transport.21.184 contrasts espectrals i540 proves backend PASS no impliquen homologació física completa. El punt de represa continua a7.14;7.15 no iniciat.

### Diagnòstic de qualificació i cost — represa 7.14 del 2026-10-21

L’[informe vigent](evidencies/pas7.14/represa-v3/validacio-represa-v3.md) i el [registre de mancances](evidencies/pas7.14/represa-v3/fonts-mancances-i-vies-v3.md) identifiquen les dades necessàries per al nominal SQM-L/TESS-W. Cap lectura nova s’ha habilitat. Els perfils antics i nous de lent/filtre es mantenen separats; el FWHM no delimita totes les cues.

`python -X utf8 tools/audit_photometry_nominal_step7_14_v3.py --numeric-only` retorna 0. El mateix auditor sense l’opció retorna 1 pel bloqueig científic; `--verify-manifest` comprova el candidat vigent sense escriure. El perfilador es pot executar amb `python -X utf8 tools/profile_photometry_step7_14_v3.py --output .runtime-photometry-v3/nova-mesura`, amb directori nou i fils BLAS/OMP a 1 com indica l’informe. Utilitza 13 espectres existents i zero LOS noves. El cost de 0,8 s prové sobretot de reconstruir regles de quadratura per panell; el runtime continua intacte.

![Temps de projecció i funcions perfilades, amb procedència i unitats](evidencies/pas7.14/represa-v3/cost-projeccio-v3.png)

El pas continua bloquejat. No es converteix la incertesa instrumental en error numèric, ni s’exigeix calibratge individual a una predicció nominal AB. No començar 7.15.
