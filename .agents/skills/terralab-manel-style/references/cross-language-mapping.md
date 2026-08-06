# Adaptación del estilo a otros lenguajes

## Principio

No traslades nombres de patrones de forma literal. Traslada la responsabilidad que protegen.

| Intención | Java / Spring | Python | TypeScript / Node | C# / .NET |
|---|---|---|---|---|
| Entrada de caso de uso | Controller, WS, listener | router, handler, command handler | controller, route handler, consumer | controller, endpoint, handler |
| Orquestación | Application service | use case class/function | application service/use case | application service/handler |
| Contrato sustituible | interface | `Protocol` o `ABC` | interface o abstract class | interface |
| Implementación | `XServiceImpl` o adapter | clase concreta con nombre funcional | `XAdapter`, `XService` | `XService`, `XAdapter` |
| Persistencia | repository interface + adapter | repository protocol + implementation | repository interface + implementation | repository interface + implementation |
| Integración externa | client/connector/adapter | gateway/client | client/adapter | typed client/adapter |
| DTO | record/class | dataclass, Pydantic model, TypedDict | interface/type/class | record/class |
| Error de negocio | excepción tipada con código | excepción de aplicación con código | error class discriminado | excepción o result tipado |
| Configuración | `@ConfigurationProperties` | settings tipados | schema validado | options tipadas |
| Trazabilidad | logger + auditoría | structured logging + audit port | structured logger + audit service | `ILogger` + audit service |

## Java moderno

Mantén interfaces en fronteras reales. Prefiere:

- inyección por constructor;
- configuración tipada;
- records para DTO inmutables cuando proceda;
- excepciones específicas;
- `try-with-resources`;
- paquetes por capacidad o módulo;
- tests de caso de uso con dobles de repositorio e integración.

No es obligatorio usar el sufijo `Impl` si una implementación tiene un nombre más informativo, por ejemplo `SftpDocumentStore` o `ThreeJsStarRenderer`.

## Python

Estructura orientativa:

```text
feature/
  domain/
  application/
    services.py
    ports.py
    dto.py
  infrastructure/
    repositories.py
    clients.py
  entrypoints/
    api.py
```

Reglas:

- usa `Protocol` para repositorios, gateways y motores sustituibles;
- usa `dataclass` o modelos tipados para DTO;
- el caso de uso debe leerse de arriba abajo;
- traduce excepciones de librería a errores de aplicación en el adapter o servicio adecuado;
- no conviertas cada función en una clase;
- no uses un contenedor DI si la composición explícita es suficiente.

Ejemplo de forma:

```python
class StarCatalog(Protocol):
    def load_visible(self, limiting_magnitude: float) -> list[Star]: ...

class BuildCelestialScene:
    def __init__(self, catalog: StarCatalog, projector: CelestialProjector) -> None:
        self._catalog = catalog
        self._projector = projector

    def execute(self, request: SceneRequest) -> SceneData:
        stars = self._catalog.load_visible(request.limiting_magnitude)
        projected = self._projector.project_all(stars, request.observer)
        return SceneData(stars=projected)
```

## TypeScript

Estructura orientativa:

```text
feature/
  domain/
  application/
  adapters/
  infrastructure/
```

Reglas:

- interfaces para puertos reales, no para todas las clases;
- DTO inmutables o `readonly` cuando ayuden;
- errores con `code`, `message`, `cause` y contexto;
- composición de dependencias en un módulo raíz;
- orquestadores claros, sin cadenas de operadores que oculten el proceso;
- APIs de render o red encapsuladas en adapters.

## Otros lenguajes

Conserva siempre:

1. capacidad funcional como unidad de cambio;
2. punto de entrada fino;
3. orquestador legible;
4. servicios cohesionados;
5. fronteras de infraestructura aisladas;
6. errores traducidos;
7. configuración externa;
8. trazabilidad contextual.
