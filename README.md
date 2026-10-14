# Simulador gráfico de autómatas

Aplicación para practicar AFND → AFD, derivar expresiones regulares por sistema de ecuaciones y comparar los lenguajes aceptados.

## Requisitos y ejecución

- Python 3.10 o superior con Tkinter.
- No requiere paquetes externos, internet ni servidor.
- Desde esta carpeta, ejecutar: `python app.py`.

En Windows, si `python` no está en el PATH, se puede abrir una terminal en esta carpeta y usar `py app.py`.

## Uso

1. Edita el JSON de la izquierda o abre uno guardado. El formato es `states`, `alphabet`, `initial`, `finals` y `transitions`.
2. Pulsa **Convertir AFND → AFD**. Se muestran el grafo original, el grafo determinista, la tabla y los movimientos paso a paso.
3. Pulsa **Usar AFD en módulo ER** y luego **Resolver ecuaciones**. El resultado incluye ecuaciones, regla de cada despeje y sustituciones.
4. En la primera pestaña, fija `n >= 6` y pulsa **Verificar AFND, AFD y ER**. El verificador enumera todas las cadenas hasta esa longitud.
5. Los botones de casos del anexo cargan ejemplos reproducibles.

Para representar una transición vacía se escribe `"symbol": "ε"` en una transición; no se agrega `ε` a `alphabet`.

## Pruebas automáticas

Desde esta carpeta ejecutar:

```text
python -m unittest discover -s tests -v
```

Las pruebas cubren los dos casos del Anexo A, el estado pozo y el bonus de clausura-ε.

## Archivos

- `app.py`: interfaz gráfica Tkinter.
- `automatas.py`: validación, construcción por subconjuntos, ecuaciones, Thompson y verificador.
- `caso1_afnd.json`, `caso2_af.json`: ejemplos del enunciado.
- `tests/test_automatas.py`: pruebas de referencia.
- `SPEC.md`: especificación y decisiones del proyecto.
- `ARQUITECTURA.md`: plan, modelo de datos y flujo entre módulos.
- `bitacora_prompts.md`: borrador de bitácora; el equipo debe completar su evidencia y sus datos.
- `bitacora_prompts.pdf`: versión PDF del borrador de bitácora.

## Alcance y limitaciones

Los símbolos del alfabeto se modelan como caracteres individuales. La expresión regular se obtiene desde el AFD generado y la verificación compara el AFND editado, ese AFD y el árbol de la expresión. Si se aumenta mucho `n` o el tamaño del alfabeto, la cantidad de cadenas crece exponencialmente.
