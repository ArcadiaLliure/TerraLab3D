# Pas 7.51 — Llicències comercials i registre de recursos del cel físic

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Autoritzar només codi permissiu compatible amb distribució comercial i dades amb drets comercials/redistribució verificats, mitjançant allowlist i bloqueig observable de recursos no autoritzats.

## Descripció funcional

Autoritzar només codi permissiu compatible amb distribució comercial i dades amb drets comercials/redistribució verificats, mitjançant allowlist i bloqueig observable de recursos no autoritzats.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md) i els seus documents d'arquitectura, física, llicències i validació.
- [Normes d'arquitectura](../../normes-arquitectura.md), [inventari](../../inventari-funcional.md) i codi real del repositori.
- [Dossier skyglow artificial](../../skyglow/README.md) només per compartir estat òptic i composició; no duplicar-ne el kernel.

## Objectiu

Autoritzar només codi permissiu compatible amb distribució comercial i dades amb drets comercials/redistribució verificats, mitjançant allowlist i bloqueig observable de recursos no autoritzats.

## Dependències

**Depèn de:**
- [Pas 7](../completat/pas7.md)
- [Pas 8](../completat/pas8.md)
- [Pas 8.7](../completat/pas8.7.md)

**En depenen:**
- [Pas 7.52](pas7.52-selector-cel-simulat-real.md)

## Codi existent a reutilitzar

Gestor de recursos, manifests i estat de disponibilitat existents; THIRD-PARTY.md.

## Flux tècnic

manifest de font/commit/llicència → allowlist permissiva + verificació d'obligacions, dades i transitius → port de recursos → disponibilitat tipada → UI i registre de THIRD-PARTY quan s'incorpori.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; resultats obsolets descartats i recursos GPU amb propietari i dispose.
- Les dades o llicències no verificades es publiquen com a unavailable, mai com a resultats científics inventats.
- **Risc:** Llicència del codi principal confosa amb la de submòduls o dades espectrals.
- **Rollback:** Bloquejar el recurs sense eliminar el mode simulat.

## Tasques

- [ ] Inventariar els fitxers Hillaire MIT i Bruneton BSD-3 realment reutilitzables, amb commit exacte; no importar Unreal Engine ni submòduls per inferència.
- [ ] Incorporar l'allowlist de llicències permissives compatible amb distribució comercial (MIT/BSD/Apache-2.0/dom. públic i llicències de dades aprovades), no una comprovació literal MIT/BSD.
- [ ] Registrar ROLO/USGS com a candidat preferent de domini públic amb verificació per fitxer; Copernicus/ERA5/CAMS amb producte i atribució exactes.
- [ ] Marcar ESO Sky Model (GPL) i LIME Toolbox (LGPL) com a **referències externes, no vendoring runtime** sota la política actual; no descriure GPL/LGPL com a “no comercial”.
- [ ] No introduir Hipparcos/Tycho o nous derivats Gaia sense auditar els termes del producte concret.
- [ ] Afegir un gate executable de manifests/llicències al gestor de recursos, amb diagnòstic visible de recurs no autoritzat.
- [ ] Registrar copyright, avís, redistribució, checksum i procedència per shaders, LUT, espectres i dades solars/lunars.
- [ ] Mantenir THIRD-PARTY.md sense declarar incorporacions inexistents; actualitzar-lo en el moment de copiar codi real.

## Criteri de sortida

El gate de llicències funciona i impedeix activar recursos no autoritzats; l'auditoria documental té fonts i obligacions comprovables.

## Proves i evidències obligatòries

- [ ] Manifest comercial permès per allowlist permissiva (MIT/BSD/Apache-2.0/dom. públic/dades compatibles), avisos complets i rebuig de dades amb drets no verificats.
- [ ] Recurs unavailable observable, cap descàrrega/vendoring automàtic d'assets sense llicència.
- [ ] No es copia codi propietari d'Unreal Engine.
- [ ] Evidències reproduïbles sota docs/evidencies/pas7.51/ quan s'implementi.
- [ ] Executar tools/validate_docs.py i les regressions afectades abans de completar.

## Fora d'abast

Incorporació de shaders i dades físiques abans del gate legal.

## Instrucció per a Codex

manifest de font/commit/llicència → allowlist permissiva + verificació d'obligacions, dades i transitius → port de recursos → disponibilitat tipada → UI i registre de THIRD-PARTY quan s'incorpori. Respectar els límits de la vertical 7.51+, les llicències comercials i el mode simulat permanent. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a completat/.
