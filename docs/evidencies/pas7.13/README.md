# Evidències del Pas7.13 — Camp angular i DomeProfile

**FAIL angular; pas pendent i funcionalitat parcial.** [Informe científic](validacio-camp-angular.md),[veredicte](gate-angular-final.json),[criteri immutable](criteri-angular-preregistrat-v1.json).952contrasts de transport PASS no homologuen la reconstrucció.

Reproducció des de l'arrel:

```powershell
python tools/validate_angular_step7_13.py --part summary
python tools/audit_angular_step7_13.py --strict
python tools/plot_dome_step7_13.py
```

L'audit estricte retorna1 perquè el gate falla; no és una prova unitària fallida. Les figures es regeneren a partir de mesures persistides, sense recalcular milers de LOS.

Per repetir controls eliminant els fitxers de resultats només en una còpia de treball autoritzada i preservant l'arxiu original:

```powershell
python tools/validate_domain_angular_step7_13.py --part standard
python tools/validate_domain_angular_step7_13.py --part terrain
python tools/validate_angular_step7_13.py --part run
```

`run` reprèn mesures existents i torna a trobar el límit de cobertura DEM registrat; no substitueix dades absents per zero. El runner v1 original està arxivat. Els preregistres i dades originals es conserven; una campanya modificada necessita versió i punts independents nous. No reexecutar pilots COESA o malles denses sense revisar primer el cost.

[Mapa de calor](mapa-calor-azimut-elevacio.png),[error PCHIP](error-pchip-vertical.png),[oclusió](oclusio-i-zero-directes.png),[golden compartit](golden-pchip-python-typescript.json),[preservació inicial](preservacio-inicial.json),[regressions](regressions.json). Cap7.14, acceleració espacial, cache o Three.js definitiu.
