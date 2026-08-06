# Arquitectura de TerraLab3D

## Arbre de paquets

```text
TerraLab3D/
├── backend/src/terralab3d/
│   ├── domain/
│   │   ├── science/              # unitats, èpoques i precisió compartides
│   │   ├── <capacitat>/models.py
│   │   ├── <capacitat>/calculations.py
│   │   └── <capacitat>/services.py
│   ├── application/
│   │   ├── commands.py
│   │   ├── events.py
│   │   ├── use_cases/
│   │   └── ports/
│   ├── scene/                    # escena neutral i deltes
│   └── infrastructure/adapters/
├── frontend/src/
│   ├── application/
│   ├── bridge/
│   ├── contracts/
│   └── view/
│       ├── ui/
│       └── three/
├── contracts/schemas/
└── docs/
```

## Direcció de dependències

```mermaid
graph LR
    UI[Vista UI] --> FC[Controlador frontend]
    FC --> BR[Bridge tipat]
    BR --> AC[Aplicació / casos d’ús]
    AC --> DM[Domini científic]
    AC --> PT[Ports de l’aplicació]
    PT --> AD[Adaptadors d’infraestructura]
    AC --> SP[Planificador d’escena]
    SP --> SD[Delta d’escena]
    SD --> TS[Adaptador Three.js]
    TS --> GPU[GPU / WebGL]

    AD -. prohibit .-> UI
    DM -. prohibit .-> TS
    TS -. prohibit .-> DM
```

## Flux de comandes

```mermaid
sequenceDiagram
    participant U as Usuari
    participant UI
    participant F as Frontend
    participant B as Bridge
    participant A as Aplicació
    participant D as Domini
    participant S as Escena
    participant T as Three.js

    U->>UI: Canvi de temps, capa, ubicació o eina
    UI->>F: Intenció tipada
    F->>B: Comanda agrupada
    B->>A: DTO de comanda
    A->>D: Càlcul o transició pura
    D-->>A: Nou estat científic
    A->>S: Reconciliació incremental
    S-->>B: Delta petit + referències de recursos
    B-->>T: Aplicació del delta
    T-->>U: Escena retinguda renderitzada
```

## Flux d’actualització temporal

```mermaid
sequenceDiagram
    participant R as Rellotge autoritatiu
    participant A as Aplicació
    participant T as Three.js
    R->>A: Revisió temporal
    A->>T: Rotació sideral i uniforms modificats
    loop Frames visuals
        T->>T: Interpola matrius i uniforms localment
        T->>T: Renderitza sense retransmetre catàlegs
    end
```

## Flux de recursos

```mermaid
sequenceDiagram
    participant A as Aplicació
    participant P as Port/Adaptador
    participant S as Escena
    participant B as Transport binari
    participant G as Registre GPU
    A->>P: Demana dataset o recurs
    P-->>A: DTO tipat + handle de bytes
    A->>S: Registra ID i versió
    S-->>B: RegisterResource
    B->>G: ArrayBuffer/texture transferible
    G-->>A: ACK de versió
    A->>S: Crea component que referencia el recurs
```

## Flux de picking

```mermaid
sequenceDiagram
    participant P as Punter
    participant T as Three.js
    participant K as PickingSystem
    participant A as Aplicació
    P->>T: Coordenades de pantalla
    T->>K: PickRequest amb generació actual
    K-->>A: PickResult real i tipat
    A->>A: Rebutja resultats obsolets i actualitza selecció
    A-->>T: Delta de ressaltat/selecció
```

## Propietat dels càlculs

- **Domini:** astronomia, fotometria, geodèsia, òptica, horitzó, terreny i geometria esfèrica.
- **Aplicació:** ordre dels casos d’ús, cancel·lació, estat de sessió i sincronització.
- **Escena:** recursos i components neutrals, sense fórmules científiques.
- **Three.js:** projecció de pantalla, GPU, shaders visuals, càmera, interpolació i picking.
- **Infraestructura:** I/O, xarxa, catàlegs, DEM, persistència, caché i workers.

## Restriccions de rendiment

- Gaia, textures i malles són recursos persistents i versionats.
- La volta celeste gira amb transformacions/uniforms, no recalculant cada estrella.
- El moviment de càmera no travessa el bridge científic.
- El backend només publica deltes científicament necessaris.
- El snapshot complet és excepcional; el camí normal és incremental.
