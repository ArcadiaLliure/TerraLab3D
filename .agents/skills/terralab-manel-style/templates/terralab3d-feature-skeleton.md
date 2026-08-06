# Plantilla de capacidad funcional para TerraLab3D

## Hito funcional

**Capacidad añadida:** `<verbo + resultado observable>`

**Demostración visible:** `<qué verá o podrá hacer el usuario>`

**Verificación científica:** `<dato conocido, invariante o tolerancia>`

## Entradas y dependencias

- Entradas funcionales:
- Unidades:
- Sistema de coordenadas:
- Configuración:
- Datos externos:
- Revisión o versión de entrada:

## Recorrido del caso de uso

1. Recibir comando o interacción.
2. Validar entradas, unidades y disponibilidad.
3. Determinar qué resultados quedan invalidados.
4. Cargar u obtener datos necesarios.
5. Ejecutar cálculo científico, local o en worker.
6. Comprobar vigencia del resultado.
7. Construir snapshot o delta de escena.
8. Actualizar estado de escena.
9. Aplicar el delta al recurso persistente de render.
10. Publicar resultado y métricas agregadas.

## Componentes

| Componente | Capa | Responsabilidad | Dependencias permitidas |
|---|---|---|---|
| | | | |

## Fronteras

| Frontera | Contrato | Implementación inicial | Motivo del contrato |
|---|---|---|---|
| | | | |

## Estado e invalidación

- Estado fuente:
- Estado derivado:
- Cambios que invalidan el resultado:
- Estrategia: `snapshot / delta / dirty flag / reemplazo completo justificado`.
- Revisión aplicada:

## Render persistente

- Recurso creado o reutilizado:
- Actualización incremental:
- Frecuencia máxima esperada:
- Propietario:
- Método de liberación:
- Comportamiento ante pérdida de contexto:

## Worker y asincronía

- ¿Requiere worker?:
- Identificador de solicitud:
- Política de cancelación:
- Política de resultado obsoleto:
- Transferibles:
- Error traducido:

## Errores y estados esperados

| Código/estado | Situación | ¿Es error? | Respuesta |
|---|---|---|---|
| | | | |

## Observabilidad

- Inicio funcional:
- Métricas agregadas:
- Umbral de operación lenta:
- Datos prohibidos en logs:
- No registrar por elemento o frame:

## Pruebas mínimas

- [ ] cálculo conocido y tolerancia;
- [ ] unidades y conversión de coordenadas;
- [ ] caso de uso sin Three.js;
- [ ] snapshot o delta producido;
- [ ] resultado obsoleto descartado, si aplica;
- [ ] recurso liberado, si aplica;
- [ ] demostración visual reproducible.

## Criterio de finalización

La capacidad está terminada cuando funciona de extremo a extremo, es verificable científica y visualmente, no introduce cálculo pesado por frame y deja explícito el ciclo de vida de los recursos que crea.
