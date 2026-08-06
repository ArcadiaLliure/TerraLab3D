# Checklist de revisión según el estilo de Manel

## Función y entregable

- [ ] El cambio añade una capacidad funcional concreta.
- [ ] Existe una forma clara de demostrarla o verificarla.
- [ ] El hito no se limita a infraestructura interna sin resultado observable.

## Responsabilidades

- [ ] La entrada recibe y traduce; no concentra detalles técnicos.
- [ ] El orquestador coordina el caso de uso de arriba abajo.
- [ ] Cada servicio corresponde a una capacidad reconocible.
- [ ] Persistencia, red, filesystem, render y proveedores externos están aislados.
- [ ] No se han creado capas que solo reenvían llamadas sin aportar significado.

## Contratos

- [ ] Cada interfaz protege una frontera o una sustitución plausible.
- [ ] No existe una pareja interfaz/implementación puramente ceremonial.
- [ ] Los DTO expresan el contrato sin filtrar detalles innecesarios de infraestructura.

## Legibilidad

- [ ] Los nombres usan vocabulario del dominio.
- [ ] Los métodos principales se leen en orden funcional.
- [ ] Los comentarios identifican etapas o decisiones, no describen sintaxis.
- [ ] Los métodos auxiliares ocultan detalles, no la historia del caso de uso.

## Errores y recursos

- [ ] Los errores técnicos se traducen con código y contexto.
- [ ] La causa original se conserva.
- [ ] No hay excepciones ignoradas.
- [ ] Los recursos se cierran o limpian incluso en error.
- [ ] Una captura genérica solo existe en la frontera superior y termina en traducción y log.

## Configuración y seguridad

- [ ] Los valores de entorno están externalizados y validados.
- [ ] No hay secretos ni endpoints privados incrustados.
- [ ] Los logs no incluyen credenciales ni contenido sensible.
- [ ] Timeouts, reintentos y límites pertenecen al adapter o configuración adecuada.

## Trazabilidad

- [ ] Se registra el inicio y el resultado de operaciones relevantes.
- [ ] Los logs incluyen identificadores funcionales útiles.
- [ ] Los errores indican la etapa en la que se produjeron.

## Modernización

- [ ] Se usan mecanismos idiomáticos del lenguaje actual.
- [ ] No se han copiado defectos de proyectos antiguos como inyección por campos o `printStackTrace`.
- [ ] Las pruebas cubren el caso de uso y las traducciones de error, aunque la muestra histórica no permita inferir una preferencia concreta de testing.

## Núcleo TerraLab3D / científico-gráfico

Aplicar además cuando corresponda:

### Hito y fronteras

- [ ] El hito es una capacidad vertical demostrable, no solo infraestructura.
- [ ] El dominio y el cálculo no dependen de Three.js, WebGL ni UI.
- [ ] El estado científico, el estado de escena y los recursos GPU están diferenciados.
- [ ] Las unidades, precisión y sistemas de coordenadas son explícitos.

### Render persistente

- [ ] El bucle de render solo aplica cambios preparados, anima y dibuja.
- [ ] No se ejecutan cargas, persistencia ni cálculos pesados por frame.
- [ ] La escena y sus recursos se actualizan incrementalmente cuando es viable.
- [ ] Toda reconstrucción completa frecuente está medida y justificada.
- [ ] Cada geometría, material, textura, buffer y listener tiene propietario y liberación.

### Asincronía y workers

- [ ] Las tareas pesadas pueden cancelarse o quedar obsoletas de forma segura.
- [ ] Cada resultado incluye correlación o revisión de la solicitud.
- [ ] Un resultado obsoleto se descarta antes de mutar el estado vigente.
- [ ] Los DTO de worker son serializables y no contienen objetos Three.js.

### Ciencia y pruebas

- [ ] El cálculo es determinista para las mismas entradas, salvo aleatoriedad controlada.
- [ ] Se documentan tolerancias, aproximaciones y dominio de validez.
- [ ] Existe una prueba numérica con entradas conocidas.
- [ ] Existe una prueba del caso de uso sin render real.
- [ ] Existe demostración visual o prueba de integración del render.

### Observabilidad

- [ ] No hay logs por estrella, vértice o frame.
- [ ] Se miden duraciones, tamaños, invalidaciones y actualizaciones de GPU de forma agregada.
- [ ] Cancelación y obsolescencia no se registran automáticamente como errores.

