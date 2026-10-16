# Pas 7.57 — SkyView LUT RGB lineal, colorimetria i projeccions científiques

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Consolidar SkyView LUT com a textura RGB de visualització, amb colorimetria i exposició correctes i sense perdre la via espectral dels sensors.

## Descripció funcional

Consolidar SkyView LUT com a textura RGB de visualització, amb colorimetria i exposició correctes i sense perdre la via espectral dels sensors.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md) i els seus documents d'arquitectura, física, llicències i validació.
- [Normes d'arquitectura](../../normes-arquitectura.md), [inventari](../../inventari-funcional.md) i codi real del repositori.
- [Dossier skyglow artificial](../../skyglow/README.md) només per compartir estat òptic i composició; no duplicar-ne el kernel.

## Objectiu

Consolidar SkyView LUT com a textura RGB de visualització, amb colorimetria i exposició correctes i sense perdre la via espectral dels sensors.

## Dependències

**Depèn de:**
- [Pas 7.56](pas7.56-transport-atmosferic-hillaire.md)

**En depenen:**
- [Pas 7.58](pas7.58-limbe-terrestre-altura.md)

## Codi existent a reutilitzar

rendererColorPolicy.ts, skyShader.ts, PhotometricProjectionService i SkyRadianceComposer.

## Flux tècnic

transport físic → SkyView LUT RGB lineal → composició radiància compatible → exposició/tone mapping; espectres → projeccions CIE/SQM/TESS separades.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; resultats obsolets descartats i recursos GPU amb propietari i dispose.
- Les dades o llicències no verificades es publiquen com a unavailable, mai com a resultats científics inventats.
- **Risc:** Confondre canals RGB efectius Hillaire amb bandes espectrals mesurades.
- **Rollback:** Mode simulat i diagnòstic explícit de dades científiques unavailable.

## Tasques

- [ ] Definir espai RGB lineal, intensitats i unitats de la SkyView LUT, sense tone mapping en la textura.
- [ ] Fixar **perfil inicial configurable** `192×108` per SkyView; no és una constant científica. Negociar `R11G11B10F` si és renderitzable i `RGBA16F` com a fallback.
- [ ] Mesurar memòria/upload i exposar dimensions/formats en diagnòstic; la resolució angular és independent de `spectralBandCount`.
- [ ] Evitar doble gamma, doble comptatge del disc solar/lunar i suma de colors ja exposats.
- [ ] Definir spectralBandCount configurable, bandSetId, límits/ponderacions i invalidació de cache; no fixar N a 8.
- [ ] Conservar espectres solar/lunar i resposta CIE/SQM/TESS fora de la LUT RGB; mai inferir sensors des de píxels.
- [ ] Fer explícita la compatibilitat espectral amb skyglow artificial i l'estat unavailable de components no modelats.

## Criteri de sortida

La SkyView LUT visual és RGB lineal, de resolució/formats configurables, mentre la fotometria continua espectral i independent del selector.

## Proves i evidències obligatòries

- [ ] RGB lineal→exposició únic i composició lineal abans de tone mapping.
- [ ] Perfil `192×108` i formats GPU compatibles sense canviar resultats científics; pujar resolució no pot alterar SQM/TESS.
- [ ] Canvi de spectralBandCount: coherència dimensional/units i invalidació, sense benchmark de selecció de N.
- [ ] Projeccions instrumentals no canvien en alternar mode visual simulat/real.
- [ ] Evidències reproduïbles sota docs/evidencies/pas7.57/ quan s'implementi.
- [ ] Executar tools/validate_docs.py i les regressions afectades abans de completar.

## Fora d'abast

Escollir N per benchmarking o obtenir SQM a partir de RGB.

## Instrucció per a Codex

transport físic → SkyView LUT RGB lineal → composició radiància compatible → exposició/tone mapping; espectres → projeccions CIE/SQM/TESS separades. Respectar els límits de la vertical 7.51+, les llicències comercials i el mode simulat permanent. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a completat/.
