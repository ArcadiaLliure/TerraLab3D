# ADR-008 — AtmosphericOpticsProvider

- **Estat:** Accepted for implementation
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

El kernel no ha de dependre de ERA5/CAMS/API concreta.

## Decisió

Un provider resol `OpticalState` per posició/altura/temps i conserva procedència per camp.

## Conseqüències

Permet jerarquia observació→forecast→reanàlisi→climatologia→standard.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Contract tests i fallbacks per camp.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.