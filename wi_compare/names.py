"""Limpieza de nombres de BOM y de instrucciones de fabricación (WI)."""

from __future__ import annotations

import re
from pathlib import Path

MAX_LONGITUD_REFERENCIA = 50
# Prefijos delanteros habituales (se quitan en cadena: BOM CAD CE-REF → REF)
PREFIJOS_DEFECTO = ("BOM", "CAD", "NAV", "CE", "WI", "INST", "PCB", "ASSY")
EXTENSIONES_BOM = {".xls", ".xlsx", ".xlsm"}
EXTENSIONES_WI = {".docx", ".doc", ".pdf"}

# Instrucción: <referencia> [ -|/|espacio ] Instrucción de fabricación… (el resto se ignora)
PATRON_INSTRUCCION = re.compile(
    r"^(.+?)(?:\s*[-/]\s*|\s+)Instrucci[oó]n de fabricaci[oó]n",
    re.IGNORECASE,
)
PALABRAS_OMITIR_BOM = ("coordenadas",)

PATRON_FECHA_GUION = re.compile(r"[_\-\s]+(\d{4}-\d{2}-\d{2})")
PATRON_FECHA_DMY_GUION = re.compile(r"[_\-\s]+(\d{2}-\d{2}-\d{4})")
PATRON_FECHA_COMPACTA = re.compile(r"[_\-\s]+(\d{8})(?!\d)")
PATRON_FECHA_6 = re.compile(r"[_\-\s]+(\d{6})(?!\d)")
PATRON_SEPARADORES = re.compile(r"[_\-\s]+")
PRODUCT_TOKEN = re.compile(
    r"(CE-[A-Z0-9+._-]+|[A-Z]{3,}\d{2,}[A-Z0-9+]*)",
    re.I,
)


def referencia_valida(ref: str) -> bool:
    ref = ref.strip()
    return bool(ref) and len(ref) <= MAX_LONGITUD_REFERENCIA


def debe_omitir_bom(stem: str) -> bool:
    """Archivos BOM que no participan (p. ej. coordenadas)."""
    texto = stem.lower()
    return any(palabra in texto for palabra in PALABRAS_OMITIR_BOM)


def _fecha_plausible_digitos(fecha: str) -> bool:
    if not fecha.isdigit():
        return False
    if len(fecha) == 8:
        anio, mes, dia = int(fecha[:4]), int(fecha[4:6]), int(fecha[6:8])
        return 1990 <= anio <= 2100 and 1 <= mes <= 12 and 1 <= dia <= 31
    if len(fecha) == 6:
        mes, dia = int(fecha[2:4]), int(fecha[4:6])
        return 1 <= mes <= 12 and 1 <= dia <= 31
    return False


def _fecha_plausible_dmy(fecha: str) -> bool:
    partes = fecha.split("-")
    if len(partes) != 3 or not all(p.isdigit() for p in partes):
        return False
    dia, mes, anio = int(partes[0]), int(partes[1]), int(partes[2])
    return 1990 <= anio <= 2100 and 1 <= mes <= 12 and 1 <= dia <= 31


def _quitar_prefijos(texto: str, prefijos: tuple[str, ...]) -> str:
    t = texto.strip()
    while True:
        cambiado = False
        for prefijo in prefijos:
            for sep in ("-", "_", " "):
                cabecera = f"{prefijo}{sep}"
                if t.upper().startswith(cabecera.upper()):
                    t = t[len(cabecera) :].lstrip()
                    cambiado = True
            if t.upper() == prefijo.upper():
                t = ""
                cambiado = True
        if not cambiado:
            break
    return t.strip()


def _quitar_fechas_finales(texto: str) -> str:
    t = texto.strip()
    while True:
        cambiado = False

        m = PATRON_FECHA_GUION.search(t)
        if m:
            t = t[: m.start()].strip()
            cambiado = True
            continue

        m = PATRON_FECHA_DMY_GUION.search(t)
        if m and _fecha_plausible_dmy(m.group(1)):
            t = t[: m.start()].strip()
            cambiado = True
            continue

        m = PATRON_FECHA_COMPACTA.search(t)
        if m and _fecha_plausible_digitos(m.group(1)):
            t = t[: m.start()].strip()
            cambiado = True
            continue

        m = PATRON_FECHA_6.search(t)
        if m and _fecha_plausible_digitos(m.group(1)):
            t = t[: m.start()].strip()
            cambiado = True
            continue

        for n in (8, 6):
            if len(t) > n and t[-n:].isdigit() and _fecha_plausible_digitos(t[-n:]):
                candidato = t[:-n].strip()
                if candidato:
                    t = candidato
                    cambiado = True
                    break

        if not cambiado:
            break

    return t.strip().strip("-_")


def _normalizar_separadores(texto: str) -> str:
    t = PATRON_SEPARADORES.sub("-", texto.strip())
    return t.strip("-")


def limpiar_referencia(stem: str, prefijos_extra: tuple[str, ...] = ()) -> str:
    """Quita prefijos (BOM, CE, WI, …) y fechas; devuelve la referencia limpia."""
    texto = stem.strip()
    m = PATRON_INSTRUCCION.match(texto)
    if m:
        texto = m.group(1).strip()

    prefijos = tuple(dict.fromkeys(PREFIJOS_DEFECTO + prefijos_extra))
    texto = _quitar_prefijos(texto, prefijos)
    texto = _quitar_fechas_finales(texto)
    texto = _normalizar_separadores(texto)
    texto = _quitar_fechas_finales(texto)
    return texto


def extraer_desde_bom(stem: str, prefijos_extra: tuple[str, ...] = ()) -> str | None:
    if debe_omitir_bom(stem):
        return None
    ref = limpiar_referencia(stem, prefijos_extra)
    return ref if referencia_valida(ref) else None


def _parece_codigo(texto: str) -> bool:
    if PRODUCT_TOKEN.search(texto or ""):
        return True
    return bool(re.search(r"[A-Za-z]", texto) and re.search(r"\d", texto))


def extraer_desde_wi(stem: str, prefijos_extra: tuple[str, ...] = ()) -> str | None:
    """
    Acepta el patrón «Instrucción de fabricación» o un nombre con código de producto.
    Así entran tanto el formato largo como WI cortas (CE-BOARD-AX-001.docx).
    """
    texto = stem.strip()
    if PATRON_INSTRUCCION.match(texto):
        ref = limpiar_referencia(texto, prefijos_extra)
        return ref if referencia_valida(ref) else None

    ref = limpiar_referencia(texto, prefijos_extra)
    if not referencia_valida(ref):
        return None
    if _parece_codigo(stem) or _parece_codigo(ref):
        return ref
    return None


def parsear_prefijos_extra(texto: str) -> tuple[str, ...]:
    partes = [p.strip().upper() for p in texto.split(",") if p.strip()]
    return tuple(dict.fromkeys(partes))


def clave_ref(ref: str, ignorar_mayusculas: bool) -> str:
    return ref.upper() if ignorar_mayusculas else ref


def nombre_archivo(ruta: str) -> str:
    return Path(ruta).name
