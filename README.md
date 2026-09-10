# Comparador_DOC

Herramienta local para ver **qué instrucciones de fabricación faltan** frente a las BOM de una carpeta.

Elige dos carpetas: una con Excel de BOM y otra con instrucciones (Word o PDF). El programa **no abre esos archivos**; solo lee los nombres, limpia la referencia y cruza.

No es el comparador de componentes. Aquel entra en el Excel y compara piezas. Este solo responde: esta placa tiene BOM, ¿tiene también instrucción?

---

## En otro PC

Copia la carpeta `dist\Comparador_DOC` y abre `Comparador_DOC.exe`. No hace falta Python.

Para generar el exe en un PC con Python: `build_exe.bat`.

---

## En este PC (con Python)

```bat
abrir_comparador.bat
```

Se abre el navegador en `http://127.0.0.1:8770`.

Desde consola, sin interfaz:

```bat
python -m wi_compare --bom "D:\BOMs" --wi "D:\Instrucciones" --out faltan.xlsx
```

---

## Cómo se usa

1. Indica la carpeta de BOM y la de instrucciones: pega la ruta, arrástrala o pulsa el recuadro.
2. **Comparar**. Si las rutas ya estaban guardadas, se lanza solo al abrir.
3. Mira primero **Faltan WI**.
4. **Descargar Excel** o **Imprimir** la pestaña que tengas abierta.

No se suben ni se copian documentos. El filtro de la tabla solo busca en el resultado, no cambia el cruce.

| Resultado | Significado |
| --- | --- |
| Faltan WI | Hay BOM y no hay instrucción |
| Completas | Hay BOM e instrucción |
| WI sin BOM | Hay instrucción y no hay BOM |
| No reconocidos | El nombre no se pudo convertir en referencia |

---

## Cómo se obtiene la referencia

Del nombre se quitan prefijos habituales (`BOM`, `CAD`, `NAV`, `CE`, `WI`, `INST`, `PCB`, `ASSY`), fechas y el texto que vaya detrás de la fecha. `_`, `-` y espacios se tratan igual. Mayúsculas y minúsculas no importan.

Así coinciden, por ejemplo:

- `BOM CAD CE-PRODUCTO-001_2024-03-01.xlsx`
- `CE-PRODUCTO-001 Instrucción de fabricación.docx`

ambos como `PRODUCTO-001`.

Una instrucción corta (`CE-PRODUCTO-001.docx`) también entra si el nombre parece un código de producto.

Se ignoran archivos con `coordenadas` en el nombre. Varios BOM de la misma placa se agrupan en una referencia.

---

## Subcarpetas

Se recorren siempre.

- BOM en subcarpeta = versión antigua. No exige instrucción y no aparece en Faltan WI.
- Instrucción en subcarpeta = válida si la referencia coincide. En Completas se marca en naranja.

---

## Desarrollo

```
wi_compare/            Logica, API e interfaz
tests/                 Pruebas
packaging/             Receta del exe
.github/workflows/     Tests en cada push
pyproject.toml
```

```bat
python -m pip install -e ".[dev]"
python -m pytest
python -m wi_compare --web
```

`dist/` y `build/` no se suben al repositorio.
