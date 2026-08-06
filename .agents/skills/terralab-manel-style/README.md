# TerraLab Manel Style

Skill específico para TerraLab3D, creado combinando el esqueleto arquitectónico del proyecto con patrones extraídos de dos proyectos escritos por Manel:

- `ECOPIA.zip`
- `0463-PICA-NTBROKER.zip`

El análisis separó código de aplicación de fuentes generadas por JAXB, Swagger, Hibernate, WSDL, documentación HTML, binarios y metadatos Git.

## Instalación

Copia la carpeta `terralab-manel-style` en el directorio de skills del agente o herramienta que utilices. El archivo principal es `SKILL.md`.

## Uso recomendado

Activa el skill cuando trabajes en TerraLab3D para:

- diseñar hitos funcionales progresivos y verificables;
- generar código coherente con la arquitectura del proyecto y con la forma de programar de Manel;
- mantener separados dominio científico, cálculo, estado de escena y render;
- implementar escenas persistentes, workers, recursos GPU e invalidaciones;
- revisar código generado por IA para evitar estilos ajenos o arquitectura ornamental;
- implementar componentes en Python, TypeScript, Java u otros lenguajes sin perder la misma intención arquitectónica.

## Archivos

- `SKILL.md`: instrucciones operativas.
- `references/analysis-report.md`: evidencia y conclusiones.
- `references/cross-language-mapping.md`: equivalencias entre lenguajes.
- `references/review-checklist.md`: checklist general y científico-gráfica.
- `references/terralab3d-profile.md`: reglas específicas para TerraLab3D.
- `templates/feature-skeleton.md`: plantilla general para una capacidad nueva.
- `templates/terralab3d-feature-skeleton.md`: plantilla de hito científico-gráfico.

## Identidad del skill

Este paquete ya no se presenta como una descripción general del estilo de Manel. Su identidad es híbrida y específica: **TerraLab3D + estilo de Manel**. Las decisiones propias de escena persistente, actualización incremental, workers, recursos GPU, unidades científicas y pruebas numéricas forman parte del núcleo del skill, no de una extensión opcional.
