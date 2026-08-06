# Plantilla de una capacidad funcional

## Hito funcional

**Capacidad añadida:** `<verbo + resultado observable>`

**Demostración:** `<cómo se comprueba que funciona>`

## Recorrido principal

1. Recibir `<entrada>`.
2. Validar `<reglas mínimas>`.
3. Obtener `<datos/configuración>`.
4. Ejecutar `<transformación o cálculo>`.
5. Persistir/publicar/renderizar `<resultado>`.
6. Construir `<respuesta o evento>`.
7. Registrar `<traza final>`.

## Componentes

### Entrada

- Nombre:
- Responsabilidad:
- No debe conocer:

### Orquestador

- Nombre:
- Método público:
- Dependencias:
- Resultado:

### Servicios de capacidad

| Servicio | Responsabilidad | Contrato necesario |
|---|---|---|
| | | sí/no y motivo |

### Fronteras externas

| Frontera | Puerto/contrato | Implementación |
|---|---|---|
| | | |

### Datos y DTO

- Entrada:
- Salida:
- Entidades o value objects:

## Errores

| Código | Situación | Causa técnica posible | Respuesta |
|---|---|---|---|
| | | | |

## Trazabilidad

- Inicio:
- Etapas relevantes:
- Finalización:
- Datos prohibidos en logs:

## Pruebas mínimas

- recorrido correcto;
- validación fallida;
- error de integración traducido;
- limpieza de recursos;
- resultado observable del hito.
