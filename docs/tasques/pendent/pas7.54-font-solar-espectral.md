# Pas 7.54 — Font solar física i irradiància espectral

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Proporcionar una font solar espectral amb irradiància, distància, disc, extinció i procedència, independent de l'aproximació RGB visual.

## Descripció funcional

Proporcionar una font solar espectral amb irradiància, distància, disc, extinció i procedència, independent de l'aproximació RGB visual.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md) i els seus documents d'arquitectura, física, llicències i validació.
- [Normes d'arquitectura](../../normes-arquitectura.md), [inventari](../../inventari-funcional.md) i codi real del repositori.
- [Dossier skyglow artificial](../../skyglow/README.md) només per compartir estat òptic i composició; no duplicar-ne el kernel.

## Objectiu

Proporcionar una font solar espectral amb irradiància, distància, disc, extinció i procedència, independent de l'aproximació RGB visual.

## Dependències

**Depèn de:**
- [Pas 7.53](pas7.53-optica-observador-altura.md)

**En depenen:**
- [Pas 7.55](pas7.55-font-lunar-espectral.md)

## Codi existent a reutilitzar

Efemèrides Pas 8, eclipsis Pas 9, il·luminació Pas 8.7 i optical state del Pas 7.53.

## Flux tècnic

efemèrides Pas 8 + distància Sol–Terra + font espectral autoritzada → SolarRadianceSource → il·luminació directa/port atmosfèric.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; resultats obsolets descartats i recursos GPU amb propietari i dispose.
- Les dades o llicències no verificades es publiquen com a unavailable, mai com a resultats científics inventats.
- **Risc:** Confondre RGB visual amb irradiància espectral o usar taules solars amb drets desconeguts.
- **Rollback:** Conservar il·luminació actual com a mode simulat.

## Tasques

- [ ] Reutilitzar posició topocèntrica solar i geometria de disc autoritatives, sense efemèrides paral·leles.
- [ ] Resoldre irradiància espectral i dependència de distància amb unitats i calibratge verificables.
- [ ] Distingir disc directe, transmissió atmosfèrica, dispersió i ombra terrestre/eclipsi.
- [ ] Publicar espectre/bandSetId i revisió per a fotometria; no obtenir l'espectre a partir de SkyView RGB.
- [ ] Fer observable el valor físic de la font i la seva disponibilitat sense canviar el shader simulat.

## Criteri de sortida

Font solar física versionada i mesurable, consumible pel solver i per la il·luminació.

## Proves i evidències obligatòries

- [ ] Llei de distància, límits d'altura solar, disc solar i casos d'eclipsi.
- [ ] Conservació d'unitats, coherència de les bandes configurades i proveniència.
- [ ] Cap recurs solar de drets comercials no verificats.
- [ ] Evidències reproduïbles sota docs/evidencies/pas7.54/ quan s'implementi.
- [ ] Executar tools/validate_docs.py i les regressions afectades abans de completar.

## Fora d'abast

Dispersió atmosfèrica completa i disc solar físic en GPU.

## Instrucció per a Codex

efemèrides Pas 8 + distància Sol–Terra + font espectral autoritzada → SolarRadianceSource → il·luminació directa/port atmosfèric. Respectar els límits de la vertical 7.51+, les llicències comercials i el mode simulat permanent. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a completat/.
