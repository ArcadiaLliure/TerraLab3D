# Pas 7.55 — Font lunar física: ROLO, fase, reflectància i espectre

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Resoldre la irradiància lunar espectral amb ROLO/USGS dins del seu domini suportat i una reflectància espacial separada per al disc/extrapolació, sense escalar simplement el Sol en RGB.

## Descripció funcional

Resoldre la irradiància lunar espectral amb ROLO/USGS dins del seu domini suportat i una reflectància espacial separada per al disc/extrapolació, sense escalar simplement el Sol en RGB.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md) i els seus documents d'arquitectura, física, llicències i validació.
- [Normes d'arquitectura](../../normes-arquitectura.md), [inventari](../../inventari-funcional.md) i codi real del repositori.
- [Dossier skyglow artificial](../../skyglow/README.md) només per compartir estat òptic i composició; no duplicar-ne el kernel.

## Objectiu

Resoldre la irradiància lunar espectral amb ROLO/USGS dins del seu domini suportat i una reflectància espacial separada per al disc/extrapolació, sense escalar simplement el Sol en RGB.

## Dependències

**Depèn de:**
- [Pas 7.54](pas7.54-font-solar-espectral.md)

**En depenen:**
- [Pas 7.56](pas7.56-transport-atmosferic-hillaire.md)

## Codi existent a reutilitzar

SolarSystemSnapshot, MoonSurfaceRenderer, Pas 8.5, Pas 9 i optical state.

## Flux tècnic

efemèrides Sol/Lluna + fase/distàncies → `LunarIrradianceProvider(ROLO)` + `MoonSurfaceReflectanceModel(Hapke/LS)` → `LunarRadianceSource` → il·luminació i port de dispersió.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; resultats obsolets descartats i recursos GPU amb propietari i dispose.
- Les dades o llicències no verificades es publiquen com a unavailable, mai com a resultats científics inventats.
- **Risc:** Albedo constant o escala RGB presentada com a model lunar científic.
- **Rollback:** Marcar font lunar física unavailable sense alterar mode simulat.

## Tasques

- [ ] Reutilitzar orientació lunar, fase, distàncies i eclipsis ja autoritatius.
- [ ] Implementar `LunarIrradianceProvider` amb ROLO/USGS com a autoritat d'irradiància integrada en disc dins del domini observacional aproximat `|phaseAngle| <= 90°`, amb fase, libració i distàncies.
- [ ] Separar `MoonSurfaceReflectanceModel`: Hapke com a model preferent i Lommel-Seeliger com a fallback mínim per distribuir brillantor sobre el disc.
- [ ] Per `|phaseAngle| > 90°`, usar la ruta reflectiva/extrapolada, calibrada per continuïtat i amb `quality=extrapolated` + incertesa ampliada; no presentar-la amb la mateixa confiança que ROLO.
- [ ] Mantenir separats error numèric/interpolació i incertesa física/absoluta de ROLO.
- [ ] Separar disc directe, dispersió atmosfèrica lunar i llum lunar sobre terreny.
- [ ] Permetre model simplificat només si queda etiquetat com a aproximació, mai com a calibratge científic complet.
- [ ] Publicar disponibilitat i dades físiques versionades per a instruments.

## Criteri de sortida

La font lunar és independent, reproduïble i observable amb fase i distància.

## Proves i evidències obligatòries

- [ ] Lluna plena, 30°, 60°, 90°, >90°, creixent/menguant, perigeu/apogeu i eclipsi.
- [ ] Dins del domini ROLO, error numèric/interpolació de software `<=0.5 %` respecte dels punts/fixtures de referència; **no** interpretar aquest gate com exactitud absoluta de ROLO.
- [ ] Continuïtat al voltant de 90° i `quality=extrapolated` fora del domini.
- [ ] Resposta espectral/irradiància coherent amb la geometria i unitats.
- [ ] Cap conversió de SkyView RGB a espectre lunar.
- [ ] Evidències reproduïbles sota docs/evidencies/pas7.55/ quan s'implementi.
- [ ] Executar tools/validate_docs.py i les regressions afectades abans de completar.

## Fora d'abast

LUT atmosfèriques i renderer físic.

## Instrucció per a Codex

efemèrides Sol/Lluna + ROLO/USGS + Hapke/LS → LunarRadianceSource → il·luminació i port de dispersió. Respectar els límits de la vertical 7.51+, les llicències comercials i el mode simulat permanent. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a completat/.
