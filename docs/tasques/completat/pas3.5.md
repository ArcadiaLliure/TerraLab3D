# Pas 3.5 — Càmera translacional, mode caminar i mode avió

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** càmera translacional, mode caminar i mode avió implementat, verificat i observable en el repositori.

## Descripció funcional

L’usuari pot desplaçar-se físicament per l’escenari tridimensional, no només girar sobre el punt d’origen.

La càmera disposa de dos modes:

- **Caminar:** exploració local vinculada a la superfície, amb altura d’ulls i col·lisió amb el terreny.
- **Avió:** vol lliure tridimensional amb ascens, descens, pitch, yaw, roll i control de velocitat.

Els objectes pròxims mostren paral·laxi real. El terreny i els objectes locals reaccionen a la translació; el cel astronòmic es manté a distància infinita i no presenta paral·laxi.

Caminar o volar no recalcula automàticament la ubicació astronòmica, el temps sideral, les efemèrides, Gaia, la Via Làctia, NGC, la contaminació lumínica ni els datasets geogràfics.

## Fonts a consultar

### TerraLab `main`, només en mode lectura

- `TerraLab/ui/astro_canvas.py`
- `TerraLab/ui/canvas_mixins/interaction.py`
- `TerraLab/ui/widget_init_helpers.py`
- `TerraLab/scene/camera.py`, si existeix
- `TerraLab/scene/projection.py`, si existeix
- proves de càmera, interacció, projecció i lifecycle

### TerraLab3D

- controlador de càmera;
- render loop;
- host Three.js;
- arbre de l’escena;
- contractes del bridge;
- HUD;
- listeners de teclat i ratolí;
- resize, focus, `visibilitychange` i shutdown;
- terreny tècnic i proves de les fases 1–3.

## Objectiu

Afegir translació tridimensional real a la càmera mitjançant un sistema local en metres, amb mode caminar i mode avió, sense alterar l’autoritat científica de Python ni introduir recàlculs científics durant la navegació.

La fase ha de preparar l’arquitectura futura de DEM, malles, picking de superfície, col·lisions, LOD, prefetch i reubicació explícita de l’observador.

---

## Dependències

**Depèn de:**
- [Pas 1 — Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js](pas1.md)

**En depenen:**
- [Pas 38 — Homologació final, recuperació i rendiment](../pendent/pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** Models, coordinadors i renderers Three.js del repositori.
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Integració domini Python → bridge de missatges/binari → escena Three.js persistent.

## Errors, cancel·lació i recursos

Gestió de recursos amb `dispose()`, cancel·lació cooperativa i degradació controlada en cas d'absència de dades.

## Tasques

- [x] Implementació i integració completa de càmera translacional, mode caminar i mode avió.

## Criteri de sortida

- [ ] La càmera presenta translació real.
- [ ] El mode caminar funciona.
- [ ] El mode avió funciona.
- [ ] El canvi de mode és estable.
- [ ] El món local mostra paral·laxi i el cel no.
- [ ] El moviment és consistent entre FPS.
- [ ] La càmera no surt de la zona carregada.
- [ ] La càmera no travessa el terreny.
- [ ] Caminar manté físicament `groundHeightM + eyeHeightM` sobre qualsevol superfície vàlida.
- [ ] Caminar segueix pujades i baixades sense flotació ni penetració.
- [ ] El moviment caminant respecta pendent màxim i step màxim.
- [ ] El smoothing és exclusivament visual i no altera la pose física.
- [ ] `TerrainSampler` es pot substituir sense modificar `GroundFollower` ni `NavigationController`.
- [ ] El mode avió reutilitza `TerrainSampler` només per clearance / anti-penetració.
- [ ] El botó SVG persona / avió i la drecera F romanen sincronitzats.
- [ ] Volar permet ascens, descens i roll.
- [ ] El reset és exacte i segur.
- [ ] La navegació no recalcula ciència.
- [ ] La navegació no reenvia catàlegs.
- [ ] Python no rep missatges per frame.
- [ ] No es recrea l’escena ni la càmera.
- [ ] No hi ha tecles, timers o listeners pendents.
- [ ] Els logs MGP són útils i no excessius.
- [ ] Totes les proves passen.

---

## Proves i evidències obligatòries

- [ ] Vídeo caminant i corrent sobre pujades i baixades.
- [ ] Vídeo demostrant grounding sense flotació ni penetració.
- [ ] Vídeo mostrant bloqueig per pendent excessiva o obstacle massa alt.
- [ ] Vídeo canviant a mode avió amb el botó SVG persona / avió i amb F.
- [ ] Vídeo sobrevolant, pujant, baixant i aplicant roll.
- [ ] Vídeo tornant a caminar sobre superfície segura.
- [ ] Vídeo movent-se amb la timeline activa.
- [ ] Prova que els recursos celestes no es retransferixen.
- [ ] Prova que Python no rep missatges a 60 Hz.
- [ ] Prova equivalent a 30, 60 i 144 FPS.
- [ ] Prova de blur, visibilitychange, límits, sostre i col·lisió.
- [ ] Mesures P50/P95.
- [ ] Prova d’arquitectura que substitueix un `TerrainSampler` fake sense canviar `GroundFollower`.
- [ ] Traça MGP de preparació, canvi de mode, inici i final.
- [ ] Captures del HUD en tots dos modes.
- [x] ---

## Fora d'abast

Cap funcionalitat fora d'abast addicional.

## Instrucció per a Codex

1. Executa exclusivament el Pas 3.5.
2. Conserva íntegrament els Passos 1–3.
3. Utilitza TerraLab `main` només com a referència en mode lectura.
4. No converteixis el moviment local en reubicació científica.
5. No enviïs la càmera a Python per cada frame.
6. No facis polling de terreny a Python mentre l’usuari es mou.
7. No introdueixis streaming de tiles si no és necessari.
8. No implementis una simulació aeronàutica completa.
9. Mantén la UI equivalent a TerraLab.
10. No afegeixis controls visuals desconnectats.
11. Implementa el canvi de mode amb un botó SVG persona / avió; `F` és només la drecera equivalent.
12. No facis que `NavigationController` depengui de `TechnicalTerrainSampler` ni del raycaster concret.
13. No suavitzis la Y física per resoldre el grounding; la pose física queda exactament enganxada al terreny i el smoothing és només visual.
14. Reutilitza `TerrainSampler` tant en caminar com en vol, amb semàntiques diferents.
15. No implementis encara `DEMTerrainSampler`; deixa el contracte preparat.
16. No marquis cap casella sense evidència.
17. No comencis el Pas 4.

## Treball pendent

Cap després del criteri de sortida.
