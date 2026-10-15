# Arquitectura y plan de trabajo

## Decisión técnica

Python 3 + Tkinter en una sola aplicación local. Se eligió por ser la alternativa recomendada en el parcial, evitar descargas y mantener toda la lógica en la biblioteca estándar.

## Estructura

```text
SimuladorAutomatas/
├── app.py                    # interfaz, editor JSON, grafos y navegación
├── automatas.py              # funciones puras y algoritmos
├── caso1_afnd.json           # referencia AFND → AFD
├── caso2_af.json             # referencia AF → ER
├── tests/test_automatas.py   # pruebas automáticas
├── SPEC.md                   # requisitos y casos límite
├── ARQUITECTURA.md           # este documento
├── README.md                 # ejecución y uso
└── bitacora_prompts.md       # registro preliminar para completar
```

## Modelo de datos

Cada autómata se representa con un diccionario JSON:

- `states`: lista de nombres únicos.
- `alphabet`: lista ordenada de símbolos de un carácter.
- `initial`: un nombre de estado de `states`.
- `finals`: lista de nombres de estado.
- `transitions`: lista de objetos con origen, símbolo y destino.
- `ε` puede aparecer como `symbol` de una transición vacía, pero nunca en `alphabet`.

La misma forma se usa para el AFND de entrada y el AFD generado, lo que permite conectar los módulos sin transformar datos a mano.

## Flujo de datos

```text
JSON editado
    │ validar
    ▼
AFND ── construcción de subconjuntos ──► AFD + traza
  │                                      │
  │ simulación                            ├── tabla y grafo
  │                                      └── sistema de ecuaciones
  │                                                │
  └──────────────────────── verificador ◄── ER ◄──┘
```

## Responsabilidad de cada módulo

- `automatas.py`: valida entradas, calcula clausuras-ε, convierte por subconjuntos, simula ambos autómatas, resuelve ecuaciones con el lema de Arden, genera el AFND de Thompson de la ER y enumera cadenas para verificar equivalencia.
- `app.py`: adapta esas funciones a widgets Tkinter. Mantiene el cálculo de la verificación en un hilo de trabajo para que la ventana siga respondiendo.
- `tests/test_automatas.py`: comprueba los resultados del anexo, el pozo y el bonus ε.



## Decisiones a validar por el equipo

- Revisar si en clase se exige una notación concreta para las ecuaciones o para la cadena vacía (`λ`/`ε`).
- Aprobar el stack Python/Tkinter y los nombres en español.
- Ejecutar la app en el equipo de cada integrante antes de grabar la demostración.
