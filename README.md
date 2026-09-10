# Comparador_DOC

Compara una carpeta de listas de materiales (BOM) con una de instrucciones de fabricación y dice **qué referencias tienen BOM pero no tienen instrucción**.

No abre el contenido de los Excel ni de los Word: cruza solo por el **nombre de archivo**.

Es distinto del **Comparador de BOM** (componentes): aquel lee el interior de los Excel; este cruza documentación.

---

## Arranque

Con Python instalado:

```bat
abrir_comparador.bat
```

o `python -m wi_compare --web`. Se abre `http://127.0.0.1:8770` (si el puerto está ocupado, prueba el siguiente).

Por consola:

```bat
python -m wi_compare --bom "D:\BOMs" --wi "D:\Instrucciones" --out faltan.xlsx
```

---

## Ejecutable (PC sin Python)

1. En un PC con Python: `build_exe.bat`.
2. Copia **toda** la carpeta `dist\Comparador_DOC` al otro equipo.
3. Abre `Comparador_DOC.exe`.

No hace falta instalar Python en el PC de destino.

---

## Uso

1. Indica las dos carpetas (pega la ruta, arrástrala desde el Explorador o pulsa el recuadro para elegirla). **No se copian archivos**: solo se leen los nombres.
2. Al tener las dos, pulsa **Comparar** (si ya hay rutas guardadas, se compara al abrir).
3. La pestaña **Faltan WI** es la respuesta principal.
4. **Descargar Excel** exporta todas las pestañas. **Imprimir** saca la pestaña visible.

| Pestaña | Criterio |
| --- | --- |
| **Faltan WI** | Hay BOM de esa referencia y no hay instrucción. |
| **Completas** | Hay BOM e instrucción. |
| **WI sin BOM** | Hay instrucción y no hay BOM. |
| **No reconocidos** | El nombre no se pudo convertir en referencia. |

El recuadro **Filtrar referencia o archivo** solo acota la tabla ya calculada.

---

## Cómo se cruza el nombre

Se quitan prefijos habituales (`BOM`, `CAD`, `NAV`, `CE`, `WI`, `INST`, `PCB`, `ASSY`), fechas al final o en medio del nombre, y el texto que vaya detrás de esa fecha. Los separadores (`_`, `-`, espacios) se unifican. Las mayúsculas no cuentan.

Ejemplo genérico:

- `BOM CAD CE-PRODUCTO-001_2024-03-01.xlsx`
- `CE-PRODUCTO-001 Instrucción de fabricación.docx`

ambos acaban en la clave `PRODUCTO-001`.

También vale una instrucción corta (`CE-PRODUCTO-001.docx`) si el nombre lleva un código de producto.

Se omiten archivos cuyo nombre contiene `coordenadas`. Varios BOM de la misma placa se agrupan en una sola referencia.

---

## Subcarpetas

Se recorren siempre.

- Una **BOM en subcarpeta** se considera versión antigua: no exige instrucción y no entra en Faltan WI.
- Una **instrucción en subcarpeta** sí vale si la referencia coincide. En Completas ese archivo se marca en naranja.

---

## Excel de salida

Hojas **Faltan WI**, **Completas**, **WI sin BOM** y **No reconocidos**, más un resumen.

---

## Proyecto

```
wi_compare/            Aplicacion: nombres, cruce, API e interfaz
tests/                 Pruebas
packaging/             Receta PyInstaller y arranque del .exe
.github/workflows/     CI de tests
pyproject.toml         Empaquetado y herramientas
abrir_comparador.bat   Arranque web
build_exe.bat          Empaquetado
```

La sesion web vive en el propio PC. API local en `127.0.0.1` (sin autenticacion): `/api/compare`, `/api/download`, `/api/pick-folder`.

```bat
python -m pip install -e ".[dev]"
python -m pytest
python -m wi_compare --web
```

`dist/` y `build/` no van al repositorio.
