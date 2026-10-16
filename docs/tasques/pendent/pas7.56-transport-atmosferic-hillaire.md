# Pas 7.56 — Transport atmosfèric físic Hillaire per Sol i Lluna

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Portar el mètode físic de dispersió/absorció Hillaire MIT a Three.js/WebGL, sense copiar codi propietari ni reutilitzar el kernel artificial.

## Descripció funcional

Portar el mètode físic de dispersió/absorció Hillaire MIT a Three.js/WebGL, sense copiar codi propietari ni reutilitzar el kernel artificial.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md) i els seus documents d'arquitectura, física, llicències i validació.
- [Normes d'arquitectura](../../normes-arquitectura.md), [inventari](../../inventari-funcional.md) i codi real del repositori.
- [Dossier skyglow artificial](../../skyglow/README.md) només per compartir estat òptic i composició; no duplicar-ne el kernel.

## Objectiu

Portar el mètode físic de dispersió/absorció Hillaire MIT a Three.js/WebGL, sense copiar codi propietari ni reutilitzar el kernel artificial.

## Dependències

**Depèn de:**
- [Pas 7.55](pas7.55-font-lunar-espectral.md)

**En depenen:**
- [Pas 7.57](pas7.57-skyview-lut-colorimetria.md)

## Codi existent a reutilitzar

Optical state i fonts dels Passos 7.53–7.55, Three.js i render loop existents.

## Flux tècnic

AtmosphericOpticsState + fonts Sol/Lluna → transmittance LUT + multiscattering LUT → integració SkyView → radiància lineal de visualització.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; resultats obsolets descartats i recursos GPU amb propietari i dispose.
- Les dades o llicències no verificades es publiquen com a unavailable, mai com a resultats científics inventats.
- **Risc:** LUT RGB utilitzada incorrectament per sensors o shader Hillaire amb recursos no auditats.
- **Rollback:** Canvi explícit a simulated, mantenint el solver físic unavailable.

## Tasques

- [ ] Seleccionar només els shaders/algoritmes de l'exemple Hillaire MIT amb atribució i llicència verificada.
- [ ] Separar coeficients/estats físics de domini de l'avaluació GPU i recursos de render.
- [ ] Implementar transmittance i multiscattering amb claus de cache per òptica i geometria; SkyView dependent de Sol/Lluna/observador.
- [ ] Aplicar oclusió planetària i visibilitat solar als punts de dispersió; no introduir un llindar de crepuscle que apagui el transport.
- [ ] Declarar l'aproximació de tres components RGB per visualització i la ruta espectral científica independent.

## Criteri de sortida

El cel físic produeix radiància lineal actualitzable i traçable per Sol i Lluna, amb recursos GPU propietaris.

## Proves i evidències obligatòries

- [ ] Atmosfera clara/amb aerosols, zenit/horitzó, Sol alt/baix i sota l'horitzó.
- [ ] Comparació física amb casos de referència; revisió temporal i invalidació de LUT.
- [ ] Sense imports d'Unreal Engine ni recursos sense llicència comercial.
- [ ] Evidències reproduïbles sota docs/evidencies/pas7.56/ quan s'implementi.
- [ ] Executar tools/validate_docs.py i les regressions afectades abans de completar.

## Fora d'abast

Composició instrumental a partir de la LUT RGB.

## Instrucció per a Codex

AtmosphericOpticsState + fonts Sol/Lluna → transmittance LUT + multiscattering LUT → integració SkyView → radiància lineal de visualització. Respectar els límits de la vertical 7.51+, les llicències comercials i el mode simulat permanent. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a completat/.
