from __future__ import annotations

from pathlib import Path

from .models import CompareResult, FileHit, FileRef, MatchRow
from .names import (
    extraer_desde_bom,
    extraer_desde_wi,
    clave_ref,
    limpiar_referencia,
    debe_omitir_bom,
)
from .scan import (
    EXTENSIONES_BOM,
    EXTENSIONES_WI,
    archivos_desde_nombres,
    listar_boms,
    listar_wis,
    partir_boms,
)


def agrupar(
    archivos: list[FileRef],
    extractor,
    prefijos_extra: tuple[str, ...],
    filtro: str,
    ignorar_mayusculas: bool,
) -> dict[str, list[FileRef]]:
    grupos: dict[str, list[FileRef]] = {}
    filtro = filtro.strip()
    for item in archivos:
        ref = extractor(item.stem, prefijos_extra)
        if ref is None:
            continue
        if filtro:
            hay = filtro.upper() in ref.upper() if ignorar_mayusculas else filtro in ref
            if not hay:
                continue
        clave = clave_ref(ref, ignorar_mayusculas)
        grupos.setdefault(clave, []).append(item)
    return grupos


def comparar_listas(
    archivos_bom: list[FileRef],
    archivos_wi: list[FileRef],
    omitidos_bom: list[FileRef] | None = None,
    *,
    carpeta_bom: str = "",
    carpeta_wi: str = "",
    ignorar_mayusculas: bool = True,
    prefijos_extra: tuple[str, ...] = (),
    filtro: str = "",
) -> CompareResult:
    omitidos_bom = list(omitidos_bom or [])
    vigentes = [item for item in archivos_bom if not item.subcarpeta]
    obsoletas = [item for item in archivos_bom if item.subcarpeta]
    for item in obsoletas:
        if not item.relativo:
            item.relativo = item.name
        omitidos_bom.append(item)

    mapa_bom = agrupar(
        vigentes, extraer_desde_bom, prefijos_extra, filtro, ignorar_mayusculas
    )
    mapa_wi = agrupar(
        archivos_wi, extraer_desde_wi, prefijos_extra, filtro, ignorar_mayusculas
    )

    refs_bom = set(mapa_bom)
    refs_wi = set(mapa_wi)

    def fila(ref: str, boms: list[FileRef], wis: list[FileRef]) -> MatchRow:
        return MatchRow(referencia=ref, boms=boms, wis=wis)

    faltan = [fila(ref, mapa_bom[ref], []) for ref in sorted(refs_bom - refs_wi)]
    coinciden = [fila(ref, mapa_bom[ref], mapa_wi[ref]) for ref in sorted(refs_bom & refs_wi)]
    sobran = [fila(ref, [], mapa_wi[ref]) for ref in sorted(refs_wi - refs_bom)]

    rutas_bom_ok = {p.path for ps in mapa_bom.values() for p in ps}
    rutas_wi_ok = {p.path for ps in mapa_wi.values() for p in ps}

    bom_no = [
        FileHit(
            path=item.path,
            name=item.name,
            limpio=limpiar_referencia(item.stem, prefijos_extra),
        )
        for item in vigentes
        if item.path not in rutas_bom_ok
    ]
    wi_no = [
        FileHit(
            path=item.path,
            name=item.name,
            limpio=limpiar_referencia(item.stem, prefijos_extra),
        )
        for item in archivos_wi
        if item.path not in rutas_wi_ok
    ]
    omitidos = [
        FileHit(
            path=item.path,
            name=item.name,
            limpio=(
                "coordenadas"
                if debe_omitir_bom(item.stem)
                else "obsoleta (subcarpeta)" if item.subcarpeta else item.stem
            ),
        )
        for item in omitidos_bom
    ]

    return CompareResult(
        carpeta_bom=carpeta_bom,
        carpeta_wi=carpeta_wi,
        faltan=faltan,
        coinciden=coinciden,
        sobran=sobran,
        bom_no_reconocidos=bom_no,
        wi_no_reconocidas=wi_no,
        omitidos_bom=omitidos,
        n_bom_archivos=len(vigentes),
        n_wi_archivos=len(archivos_wi),
        n_bom_refs=len(refs_bom),
        n_wi_refs=len(refs_wi),
        n_bom_obsoletas=len(obsoletas),
    )


def comparar_nombres(
    items_bom: list[dict],
    items_wi: list[dict],
    *,
    ignorar_mayusculas: bool = True,
    prefijos_extra: tuple[str, ...] = (),
    filtro: str = "",
) -> CompareResult:
    brutos_bom = archivos_desde_nombres(items_bom, EXTENSIONES_BOM)
    brutos_wi = archivos_desde_nombres(items_wi, EXTENSIONES_WI)
    usar_bom, omitidos = partir_boms(brutos_bom)
    return comparar_listas(
        usar_bom,
        brutos_wi,
        omitidos,
        carpeta_bom="BOM",
        carpeta_wi="WI",
        ignorar_mayusculas=ignorar_mayusculas,
        prefijos_extra=prefijos_extra,
        filtro=filtro,
    )


def comparar_carpetas(
    carpeta_bom: str,
    carpeta_wi: str,
    *,
    ignorar_mayusculas: bool = True,
    prefijos_extra: tuple[str, ...] = (),
    filtro: str = "",
) -> CompareResult:
    archivos_bom, omitidos_bom = listar_boms(carpeta_bom)
    archivos_wi = listar_wis(carpeta_wi)
    return comparar_listas(
        archivos_bom,
        archivos_wi,
        omitidos_bom,
        carpeta_bom=carpeta_bom,
        carpeta_wi=carpeta_wi,
        ignorar_mayusculas=ignorar_mayusculas,
        prefijos_extra=prefijos_extra,
        filtro=filtro,
    )
