# Pas 19 — Modes òptics, telescopi, ocular i enquadrament instrumental

> Estat: **pendent**. Els tipus Python i les interfícies de presentació existeixen, però no estan connectats al runtime.

## Estat actual verificat

- [x] Hi ha models per instrument, sensor, forma i camp de visió, un `ConfigureOptics` i un `ScopeComponent` neutral.
- [x] Existeixen interfícies `OpticsPanel` i `ScopeLayerRenderer`.
- [ ] No existeix encara una implementació funcional dels modes ull, prismàtics i scope.

## Resultat funcional

L'usuari alterna, amb un únic control, entre ull, prismàtics i scope. El scope admet perfil telescopi o càmera, marc circular o rectangular, focal, obertura, ocular, sensor, aspecte, moviment i navegació RA/Dec sense reiniciar la càmera.

## Dependències

- [Pas 5 — Gaia i buffers persistents](../completat/pas5.md).
- [Pas 6 — picking estel·lar](../completat/pas6.md).
- [Pas 12 — cerca i focus](../completat/pas12.md).
- [Pas 13 — selecció i inspecció](../completat/pas13.md).

## Decisions tancades

- `OpticalMode` té tres modes de comportament: `eye`, `binoculars` i `scope`; telescopi/objectiu/càmera són perfils del mode `scope`, no càmeres Three.js duplicades.
- Ull conserva la navegació global actual.
- Prismàtics manté el FOV global i amplia només una mira circular sota el cursor; `scroll` canvia augment i `Ctrl+scroll` el radi visual.
- Scope usa marc circular per ocular o rectangular per sensor. `scroll` modifica l'escala òptica i `Ctrl+scroll` la mida de presentació del marc sense canviar el FOV científic.
- El cursor nadiu s'amaga mentre una mira el substitueix.
- La simulació de senyal, soroll, ISO i exposició pertany al Pas 20.

## Codi existent a reutilitzar

- Models i ports: [`optics/models.py`](../../backend/src/terralab3d/domain/optics/models.py), [`optics/calculations.py`](../../backend/src/terralab3d/domain/optics/calculations.py) i [`use_cases/optics.py`](../../backend/src/terralab3d/application/use_cases/optics.py).
- Comanda i escena: [`commands.py`](../../backend/src/terralab3d/application/commands.py) i [`components.py`](../../backend/src/terralab3d/scene/components.py).
- Frontend: [`OpticsPanel.ts`](../../frontend/src/view/ui/panels/OpticsPanel.ts), [`ScopeLayerRenderer.ts`](../../frontend/src/view/three/layers/ScopeLayerRenderer.ts), [`CameraRigImpl.ts`](../../frontend/src/view/three/CameraRigImpl.ts) i [`InputMapper.ts`](../../frontend/src/view/ui/InputMapper.ts).
- Gaia/picking: [`StarSpatialIndex.ts`](../../frontend/src/view/three/picking/StarSpatialIndex.ts) i [`star_coordinator.py`](../../backend/src/terralab3d/application/star_coordinator.py).
- Oracle TerraLab: [scope](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/widgets/telescope_scope_mode.py), [runtime òptic](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/widgets/telescope_runtime.py) i [matemàtica física](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/widgets/physical_math.py).

## Treball pendent

- [ ] Validar invariants i implementar FOV H/V/diagonal, superfície angular, augment, pupil·la de sortida i obertura per diàmetre o nombre f.
- [ ] Incloure presets 1/2.8, APS-C i full frame, aspectes automàtic, 1:1, 4:3, 3:2, 16:9, 21:9 i personalitzat.
- [ ] Implementar estat de mode independent de la càmera i transició sense salt de pose.
- [ ] Implementar mira binocular amb zoom intern i marc scope circular/rectangular retingut.
- [ ] Enrutar scroll, modificadors, arrossegament, moviment lent/ràpid i hold rate pel controlador de mode.
- [ ] Afegir selecció del centre, entrada RA/Dec i acció Go RA/Dec.
- [ ] HUD binocular: distància, azimut i elevació. HUD scope: FOV, diagonal, superfície, augment, pupil·la i estrelles dins del camp.
- [ ] Llançar consulta Gaia profunda cancel·lable quan el catàleg resident no cobreixi la magnitud requerida, mantenint reticle i càmera fluids.
- [ ] Persistir mode i paràmetres amb esquema versionat.

## Flux tècnic

Intenció UI → controlador òptic → càlcul pur → estat de sessió/revisió → delta de scope → renderer retingut. El recompte Gaia usa el recurs o índex ja carregat; una consulta profunda torna amb request ID abans d'actualitzar el HUD.

## Errors, cancel·lació i recursos

- Rebutjar focal, sensor, obertura, ocular o aspecte no vàlids amb errors de validació visibles.
- Consulta profunda: latest-wins; cancel·lació i obsolescència són estats esperats.
- El renderer és propietari de màscara, reticle, materials i targets necessaris per la mira ampliada.

## Proves

- Fórmules i presets amb fixtures de TerraLab.
- Canvi de mode sense canvi de pose ni duplicació de càmera.
- Separació entre zoom global, zoom intern i mida visual del marc.
- Recompte del camp contra Gaia i cancel·lació d'una consulta profunda.
- `dispose`, resize, DPR i rendiment en camp dens.

## Criteri de sortida

Els modes comparteixen escena i càmera, cada control té una semàntica única, els valors òptics són correctes i el scope continua interactiu mentre arriben dades profundes.

## Evidències

- [ ] Captures d'ull, prismàtics, ocular circular i sensor rectangular.
- [ ] Vídeo de scroll, `Ctrl+scroll`, arrossegament i Go RA/Dec.
- [ ] Taula de FOV/augment/pupil·la contrastada.
- [ ] Mètrica de frame i prova de cancel·lació Gaia.

## Fora d'abast

Fotometria de captura (Pas 20), base comercial de sensors ([idea per madurar](../idees-per-madurar/base-de-dades-camares-sensors.md)) i control de muntures.

## Instrucció per a Codex

Converteix els esquelets en una vertical executable sense crear una càmera o escena per mode. Conserva al backend els càlculs i al frontend la projecció, interacció i recursos visuals.
