from __future__ import annotations

from pathlib import Path

from .models import FileRef
from .names import EXTENSIONES_BOM, EXTENSIONES_WI, debe_omitir_bom


def es_archivo_raiz(relative: str) -> bool:
    """True si el archivo está en la carpeta elegida, no en una subcarpeta."""
    partes = Path(str(relative or "").replace("\\", "/")).parts
    return len(partes) <= 2


def listar_archivos(carpeta: str, extensiones: set[str]) -> list[FileRef]:
    resultados: list[FileRef] = []
    raiz = Path(carpeta)
    if not carpeta or not raiz.is_dir():
        return resultados

    for path in raiz.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith("~$") or path.name.startswith("."):
            continue
        if path.suffix.lower() not in extensiones:
            continue
        try:
            rel = path.relative_to(raiz)
        except ValueError:
            rel = Path(path.name)
        resultados.append(
            FileRef(
                path=str(path),
                name=path.name,
                stem=path.stem,
                subcarpeta=len(rel.parts) > 1,
                relativo=str(rel).replace("\\", "/"),
            )
        )
    resultados.sort(key=lambda item: item.name.lower())
    return resultados


def listar_boms(carpeta: str) -> tuple[list[FileRef], list[FileRef]]:
    return partir_boms(listar_archivos(carpeta, EXTENSIONES_BOM))


def listar_wis(carpeta: str) -> list[FileRef]:
    return listar_archivos(carpeta, EXTENSIONES_WI)


def archivos_desde_nombres(items: list[dict], extensiones: set[str]) -> list[FileRef]:
    resultados: list[FileRef] = []
    for item in items:
        nombre = Path(str(item.get("name") or "")).name
        if not nombre or nombre.startswith("~$") or nombre.startswith("."):
            continue
        if Path(nombre).suffix.lower() not in extensiones:
            continue
        relativo = str(item.get("relative") or nombre).replace("\\", "/")
        resultados.append(
            FileRef(
                path=nombre,
                name=nombre,
                stem=Path(nombre).stem,
                subcarpeta=not es_archivo_raiz(relativo),
                relativo=relativo,
            )
        )
    resultados.sort(key=lambda item: item.name.lower())
    return resultados


def partir_boms(archivos: list[FileRef]) -> tuple[list[FileRef], list[FileRef]]:
    usar: list[FileRef] = []
    omitidos: list[FileRef] = []
    for item in archivos:
        if debe_omitir_bom(item.stem):
            omitidos.append(item)
        else:
            usar.append(item)
    return usar, omitidos
