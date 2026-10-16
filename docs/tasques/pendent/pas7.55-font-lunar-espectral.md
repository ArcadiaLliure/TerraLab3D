# Pas 7.55 — Font lunar física: fase, albedo i espectre

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Resoldre irradiància lunar reflectida per geometria Sol–Lluna–observador, fase, distància i espectre, sense escalar simplement el Sol en RGB.

## Descripció funcional

Resoldre irradiància lunar reflectida per geometria Sol–Lluna–observador, fase, distància i espectre, sense escalar simplement el Sol en RGB.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md) i els seus documents d'arquitectura, física, llicències i validació.
- [Normes d'arquitectura](../../normes-arquitectura.md), [inventari](../../inventari-funcional.md) i codi real del repositori.
- [Dossier skyglow artificial](../../skyglow/README.md) només per compartir estat òptic i composició; no duplicar-ne el kernel.

## Objectiu

Resoldre irradiància lunar reflectida per geometria Sol–Lluna–observador, fase, distància i espectre, sense escalar simplement el Sol en RGB.

## Dependències

**Depèn de:**
- [Pas 7.54](pas7.54-font-solar-espectral.md)

**En depenen:**
- [Pas 7.56](pas7.56-transport-atmosferic-hillaire.md)

## Codi existent a reutilitzar

SolarSystemSnapshot, MoonSurfaceRenderer, Pas 8.5, Pas 9 i optical state.

## Flux tècnic

efemèrides Sol/Lluna + fase/distàncies + model de reflectància autoritzat → LunarRadianceSource → il·luminació i port de dispersió.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; resultats obsolets descartats i recursos GPU amb propietari i dispose.
- Les dades o llicències no verificades es publiquen com a unavailable, mai com a resultats científics inventats.
- **Risc:** Albedo constant o escala RGB presentada com a model lunar científic.
- **Rollback:** Marcar font lunar física unavailable sense alterar mode simulat.

## Tasques

- [ ] Reutilitzar orientació lunar, fase, distàncies i eclipsis ja autoritatius.
- [ ] Modelar irradiància lunar espectral amb reflectància/funció de fase explícita i incertesa.
- [ ] Separar disc directe, dispersió atmosfèrica lunar i llum lunar sobre terreny.
- [ ] Permetre model simplificat només si queda etiquetat com a aproximació, mai com a calibratge científic complet.
- [ ] Publicar disponibilitat i dades físiques versionades per a instruments.

## Criteri de sortida

La font lunar és independent, reproduïble i observable amb fase i distància.

## Proves i evidències obligatòries

- [ ] Lluna nova/plena, fases intermèdies, perigeu/apogeu i eclipsi.
- [ ] Resposta espectral/irradiància coherent amb la geometria i unitats.
- [ ] Cap conversió de SkyView RGB a espectre lunar.
- [ ] Evidències reproduïbles sota docs/evidencies/pas7.55/ quan s'implementi.
- [ ] Executar tools/validate_docs.py i les regressions afectades abans de completar.

## Fora d'abast

LUT atmosfèriques i renderer físic.

## Instrucció per a Codex

efemèrides Sol/Lluna + fase/distàncies + model de reflectància autoritzat → LunarRadianceSource → il·luminació i port de dispersió. Respectar els límits de la vertical 7.51+, les llicències comercials i el mode simulat permanent. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a completat/.
