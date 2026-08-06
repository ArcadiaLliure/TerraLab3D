# Infraestructura i adaptadors

## Propòsit

Implementar els ports definits per l’aplicació: catàlegs, efemèrides, DEM, ortofoto, cobertura, clima, contaminació lumínica, persistència, downloads, caché, workers, telemetria i transport binari.

## Regla de dependència

Els adaptadors poden importar ports i DTO del domini. El domini i l’aplicació no poden importar adaptadors.

## Criteri de migració

La lògica de TerraLab només es trasllada aquí quan és I/O, integració amb una biblioteca, planificació de tasques, caché o accés a un servei extern. Les fórmules científiques s’extreuen al paquet funcional corresponent.
