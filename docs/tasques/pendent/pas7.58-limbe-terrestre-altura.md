# Pas 7.58 — Limbe terrestre, curvatura, terminador i altura orbital

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Renderitzar la Terra i la franja atmosfèrica il·luminada pel Sol quan la càmera s'eleva, com a resultat de geometria i dispersió física.

## Descripció funcional

Renderitzar la Terra i la franja atmosfèrica il·luminada pel Sol quan la càmera s'eleva, com a resultat de geometria i dispersió física.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md) i els seus documents d'arquitectura, física, llicències i validació.
- [Normes d'arquitectura](../../normes-arquitectura.md), [inventari](../../inventari-funcional.md) i codi real del repositori.
- [Dossier skyglow artificial](../../skyglow/README.md) només per compartir estat òptic i composició; no duplicar-ne el kernel.

## Objectiu

Renderitzar la Terra i la franja atmosfèrica il·luminada pel Sol quan la càmera s'eleva, com a resultat de geometria i dispersió física.

## Dependències

**Depèn de:**
- [Pas 7.57](pas7.57-skyview-lut-colorimetria.md)

**En depenen:**
- [Pas 7.59](pas7.59-illuminacio-terreny-eclipsis.md)

## Codi existent a reutilitzar

Pas 15/16, ECEF/ENU, HorizonLayerRenderer, DemTerrainLayerRenderer i LUT física.

## Flux tècnic

observer ECEF/altura + raig de vista → intersecció Terra/atmosfera → visibilitat solar i segment tangent → dispersió/extinció → limbe/terminador.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; resultats obsolets descartats i recursos GPU amb propietari i dispose.
- Les dades o llicències no verificades es publiquen com a unavailable, mai com a resultats científics inventats.
- **Risc:** Halo dibuixat com a textura fixa o horitzó pla a gran altura.
- **Rollback:** Mode simulat amb avís de limitació, sense fals limbe físic.

## Tasques

- [ ] Calcular horitzó geomètric dependent d'altura i interseccions amb superfície/el·lipsoide/atmosfera.
- [ ] Distingir vista des de superfície, vol, estratosfera i fora de l'atmosfera; respectar DEM i oclusió de la Terra.
- [ ] Integrar raigs tangents i la il·luminació solar local al llarg de l'atmosfera; cap cercle de glow decoratiu.
- [ ] Renderitzar disc terrestre, terminador, ombra del planeta i halo diürn asimètric, amb continuïtat de transició.
- [ ] Aplicar rebasament/origen local per evitar errors de precisió GPU a escala orbital.

## Criteri de sortida

La curvatura i el limbe solar físic són visibles i geomètricament coherents a gran altura.

## Proves i evidències obligatòries

- [ ] Depressió d'horitzó acos(R/(R+h)) en cas esfèric de referència.
- [ ] Càmera sota/dins/sobre atmosfera, tangent, raigs ocults i costat nocturn.
- [ ] Halo present només on hi ha dispersió/il·luminació; sense anell uniforme i sense salts en creuar capes.
- [ ] Evidències reproduïbles sota docs/evidencies/pas7.58/ quan s'implementi.
- [ ] Executar tools/validate_docs.py i les regressions afectades abans de completar.

## Fora d'abast

Textura de cercle il·luminat que no resol transport radiatiu.

## Instrucció per a Codex

observer ECEF/altura + raig de vista → intersecció Terra/atmosfera → visibilitat solar i segment tangent → dispersió/extinció → limbe/terminador. Respectar els límits de la vertical 7.51+, les llicències comercials i el mode simulat permanent. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a completat/.
