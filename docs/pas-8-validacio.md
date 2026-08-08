# Pas 8 — validació científica i de rendiment

Data de validació: 2026-08-08. Plataforma: Windows, Python 3.13, Skyfield 1.55 i Three.js 0.179.0.

## Efemèride reproduïble

- Kernel: `de421.bsp`, resolt des de la biblioteca de dades gestionada (`data/sky/solar-system/de421.bsp`).
- SHA-256: `a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc`.
- Rang validat: 1899-07-28 — 2053-10-08.
- Dependències fixades: `skyfield==1.55`, `skyfield-data==7.0.0`.
- La càrrega usa exclusivament un fitxer local; no hi ha cap descàrrega en execució ni durant els tests.

Les fixtures offline provenen de NASA/JPL Horizons API 1.2 per a `2024-01-01T00:00:00Z`, latitud 41.189795°, longitud 1.210058° i elevació 0 m. Les toleràncies declarades són: separació equatorial i horitzontal menor de 0,01°, distància relativa `5e-5`, fase ±0,02° i magnitud ±0,08.

La comparació executable amb TerraLab `main` (`1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`) i les mateixes entrades va donar 0° de diferència Alt/Az per a Sol, Lluna i Mercury–Neptune. Els radis de Sol i Lluna difereixen 0,00000303° i 0,00000233° respectivament perquè TerraLab usa `atan(radius/distance)` i TerraLab3D usa el radi esfèric `asin(radius/distance)`.

## Mètriques

Benchmark calent de 120 snapshots consecutius amb els nou cossos:

| Mètrica | Resultat |
|---|---:|
| `ephemeris_compute_ms_p50` | 16,253 ms |
| `ephemeris_compute_ms_p95` | 19,478 ms |
| `solar_system_bridge_bytes` | 5.110 B en la prova integrada |
| `frame_ms_p50` | 6,94 ms |
| `frame_ms_p95` | 6,96 ms |
| `solar_system_entity_build_count` | 9 |
| `solar_system_material_build_count` | 9 |

Les mètriques de frame corresponen a una finestra estable de 600 frames d'una execució real de `python -m terralab3d`. Els comptadors d'entitats i materials es van mantenir en 9 després de 100 snapshots de test i durant l'execució real.

Prova integrada de concurrència i transport:

- 100 missatges de càmera amb el temps pausat: 0 snapshots solars i 0 bytes Gaia.
- 200 `camera_pose_changed` repartits entre walk i flight, amb el temps pausat: delta de requests 0, 0 snapshots solars i 0 bytes Gaia.
- Ràfega de 25 instants: 1 snapshot publicat, corresponent a l'últim instant (`2024-01-01T00:00:24Z`).
- Mètriques del coordinador en la ràfega: 30 requests totals, 23 coalescències i 1 resultat stale descartat.
- Durant la ràfega, el canvi d'observador i el canvi només atmosfèric: 0 bytes Gaia.
- El canvi d'observador va incrementar `observerGeneration` d'1 a 2; els moviments walk/flight/càmera no el modifiquen.
- El tancament integrat va completar el lifecycle del coordinador, kernel, WebSocket i servidor.

## Verificacions

- `python -m pytest backend/tests -q`: 16 tests passats.
- Tests frontend: 69 de grid, 18 de navegació i 28 del sistema solar, tots passats.
- `tsc --noEmit`, build esbuild i validador d'esquelet: sense errors.
- El navegador de revisió automatitzada no estava disponible en la sessió; l'aplicació sí que es va executar en el navegador del sistema i va reportar frames WebGL i telemetria, però no es conserva una inspecció visual/captura automatitzada.

Fonts de les dades: [NASA/JPL Horizons](https://ssd-api.jpl.nasa.gov/doc/horizons.html), [Skyfield](https://rhodesmill.org/skyfield/api.html) i [skyfield-data](https://pypi.org/project/skyfield-data/).
