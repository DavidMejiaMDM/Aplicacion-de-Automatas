# SPEC - Simulador gráfico de autómatas

## Objetivo

Aplicación local para construir y explicar la conversión de un AFND a un AFD, obtener una expresión regular de un autómata finito y comprobar por enumeración que los tres reconocen las mismas cadenas.

## Usuario y ejecución

- Público: estudiantes del curso Teoría de la Computación.
- Stack elegido: Python 3 y Tkinter, sin servidor, internet, servicios ni bibliotecas externas.
- Inicio: `python app.py` desde esta carpeta.
- La interfaz permite abrir y guardar autómatas en JSON.

## Datos de entrada

JSON con `states` (nombres únicos), `alphabet` (símbolos de un carácter), `initial`, `finals` y `transitions` (objetos `from`, `symbol`, `to`). El símbolo `ε` en una transición representa una transición vacía y no pertenece al alfabeto.

Ejemplo:

```json
{
  "states": ["q0", "q1"],
  "alphabet": ["a"],
  "initial": "q0",
  "finals": ["q1"],
  "transitions": [{"from": "q0", "symbol": "a", "to": "q1"}]
}
```

## Requisitos funcionales

1. Editar, validar, abrir y guardar un AFND desde el editor JSON.
2. Convertir usando construcción por subconjuntos. Si hay ε, aplicar clausura-ε al inicial y después de cada movimiento.
3. Mostrar la tabla de conversión, el estado pozo `∅` si es alcanzable, los grafos de origen y resultado, y el detalle de cada movimiento por símbolo.
4. Resolver el sistema de ecuaciones del autómata en el sentido de lenguajes aceptados desde cada estado. Mostrar sistema, sustituciones, simplificaciones y la regla usada, incluyendo el caso de estado final `λ` y el lema de Arden para bucles.
5. Permitir alimentar el módulo de ER con el AFD generado. También permite cargar el caso 2 del anexo.
6. Enumerar las cadenas de longitud 0 a `n`, con `n >= 6`, y comparar aceptación por el AFND, el AFD y la ER. Informar todas las cadenas discrepantes.

## Reglas y representación de expresiones

- `+`: unión; concatenación: yuxtaposición; `*`: estrella de Kleene; `λ`: cadena vacía; `∅`: lenguaje vacío.
- Las expresiones se construyen como árboles internos, no concatenando texto sin estructura.
- Para resolver ecuaciones se despeja cada estado `X` de la forma `X = A X + B` como `A*B`, y se sustituye en las demás ecuaciones hasta despejar el inicial.

## Casos límite

- Falta de transiciones para un símbolo: se transita a `∅`; este se incluye con bucle propio cuando se alcanza.
- Estados inalcanzables: se conservan en el AFND de entrada; la conversión por subconjuntos no los incluye salvo que se alcancen.
- Alfabeto de un símbolo: todas las tablas y grafos funcionan con una sola columna de símbolo.
- AFND con ε: se admite `ε` como símbolo de transición, nunca como símbolo del alfabeto.
- Inicial final: su ecuación incluye `λ` y la cadena vacía debe ser aceptada.
- Sin camino a un estado final: la ER puede ser `∅`.
- Entradas inválidas: estados duplicados, inicial/final inexistentes, símbolos fuera del alfabeto y transiciones mal formadas se rechazan con mensaje legible.

## Verificación de aceptación

Las pruebas automáticas cubren los dos casos del Anexo A, el estado pozo y clausuras-ε. La opción de verificación de la app requiere `n >= 6`; compara exhaustivamente el AFND original, el AFD generado y un autómata Thompson equivalente a la ER.

## Interfaz

Una ventana Tkinter con pestañas para conversión/verificación y para ecuaciones/ER. Incluye editor JSON, tabla, diagramas de estados, navegación por pasos y mensajes de validación.

## Criterios de aceptación

- Los casos del Anexo A producen AFD y ER equivalentes a los esperados.
- No se requieren instalaciones de paquetes ni conexión a internet.
- El estado pozo aparece cuando existe una transición sin destino.
- La verificación examina todas las cadenas desde longitud 0 hasta `n` y muestra diferencias si existen.
- Cada paso de solución de ecuaciones identifica su regla y su sustitución.
