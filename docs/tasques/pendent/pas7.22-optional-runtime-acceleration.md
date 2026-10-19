# Pas 7.22 — Skyglow físic — Decisió i backend opcional LUT/precomputació/FFT

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Decidir acceleracions globals o backends addicionals (GPU, compilació nativa, LUT/precomputació/FFT) només si la ruta directa, la vectorització, el multicore i la cache no compleixen els SLO aprovats; no duplicar innecessàriament capacitats ja homologades a 7.18–7.21.

## Dependències

7.21

## Referències obligatòries

- [02-arquitectura-integracio.md](../../skyglow/02-arquitectura-integracio.md)
- [03-pipeline-python-typescript-threejs.md](../../skyglow/03-pipeline-python-typescript-threejs.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

## Tasques

- [ ] Fixar i preregistrar els SLO de producte aprovats, amb propietari, plataforma i condicions de mesura, abans d'usar-los per decidir si cal LUT/precomputació/FFT; sense requisit aprovat, bloquejar 7.22.
- [ ] Executar perfil de rendiment amb la ruta actual i comparar-lo amb aquests SLO congelats.
- [ ] Si els SLO ja es compleixen, tancar el pas com `no necessari` amb evidència i no afegir complexitat.
- [ ] Si no es compleixen, seleccionar LUT/precomputació/FFT només dins hipòtesis matemàtiques declarades.
- [ ] Comparar backend accelerat contra la ruta directa en error radiomètric/angular i casos límit.
- [ ] Definir fallback fora de domini i invalidació per versions.
- [ ] Proposar SLO diferenciats de presentació (FPS), primera resposta, refinament i latència de canvis de K/mescla/posició/atmosfera, amb dispositius i càrregues representatius; les metes orientatives 60 FPS, 1–3 s i 10–30 s no són automàticament els SLO aprovats.
- [ ] Amb SLO aprovats, estudiar si cal un backend addicional compilat/Numba/natiu, GPU compute o combinacions amb LUT/precomputació/FFT, incloent temps de transferència, precisió float, latència i memòria; comparar amb ruta directa i configuracions multicore dels passos anteriors.

## Criteri de sortida

Els SLO provenen d'un requisit de producte aprovat i precedeixen la decisió d'acceleració; si no existeixen, 7.22 queda bloquejat. Després, o bé hi ha evidència que no cal backend addicional, o bé existeix un backend accelerat homologat contra la ruta directa amb domini/error/fallback explícits.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.22/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

FFT no és física nova. Si falla la invariància requerida, no la facis servir.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
