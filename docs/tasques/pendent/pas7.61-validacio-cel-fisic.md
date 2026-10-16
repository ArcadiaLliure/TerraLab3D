# Pas 7.61 — Validació física solar/lunar, color, altitud i limbe

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Validar radiància, color, geometria, composició i fotometria de la configuració física activa sense benchmarks per decidir N.

## Descripció funcional

Validar radiància, color, geometria, composició i fotometria de la configuració física activa sense benchmarks per decidir N.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md) i els seus documents d'arquitectura, física, llicències i validació.
- [Normes d'arquitectura](../../normes-arquitectura.md), [inventari](../../inventari-funcional.md) i codi real del repositori.
- [Dossier skyglow artificial](../../skyglow/README.md) només per compartir estat òptic i composició; no duplicar-ne el kernel.

## Objectiu

Validar radiància, color, geometria, composició i fotometria de la configuració física activa sense benchmarks per decidir N.

## Dependències

**Depèn de:**
- [Pas 7.60](pas7.60-integracio-three-bridge.md)

**En depenen:**
- [Pas 7.62](pas7.62-homologacio-cel-fisic.md)

## Codi existent a reutilitzar

Docs cel-fisic/04, solver de referència, tests de Passos 7.1–7.28 i 8.7.

## Flux tècnic

escenaris reproduïbles → solver físic + referències analítiques/numèriques + dades calibrades → errors i incertesa → diagnòstic de validesa.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; resultats obsolets descartats i recursos GPU amb propietari i dispose.
- Les dades o llicències no verificades es publiquen com a unavailable, mai com a resultats científics inventats.
- **Risc:** Declarar el model científic només per la qualitat estètica de la imatge.
- **Rollback:** Mantenir physical no homologat i simulated disponible.

## Tasques

- [ ] Definir fixtures dia/crepuscle/nit lunar, aerosols, altituds i terminador amb dades i unitats.
- [ ] Contrastar transmittance, dispersió, irradiància i llum difusa amb solucions de referència i toleràncies declarades.
- [ ] Comparar geometria d'horitzó, limbe i ombra a superfície, avió, estratosfera i òrbita.
- [ ] Validar projeccions de sensor des d'espectre, no de RGB, i separar fons natural del skyglow artificial.
- [ ] Publicar diagnòstic de validesa/limitacions i resultats reproducibles; cap sweep de nombre de bandes.

## Criteri de sortida

Hi ha evidències de física i limitacions quantificades sense atribuir precisió espectral a la LUT RGB.

## Proves i evidències obligatòries

- [ ] Golden radiomètrics i de geometria, escenaris d'eclipsi i llum lunar.
- [ ] Convergència numèrica del solver amb configuració espectral activa; no benchmark N=3/6/8/12.
- [ ] Mètriques CPU/GPU de runtime i regressió visual del mode simulat.
- [ ] Evidències reproduïbles sota docs/evidencies/pas7.61/ quan s'implementi.
- [ ] Executar tools/validate_docs.py i les regressions afectades abans de completar.

## Fora d'abast

Escollir el nombre de bandes amb benchmarks.

## Instrucció per a Codex

escenaris reproduïbles → solver físic + referències analítiques/numèriques + dades calibrades → errors i incertesa → diagnòstic de validesa. Respectar els límits de la vertical 7.51+, les llicències comercials i el mode simulat permanent. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a completat/.
