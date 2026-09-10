from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compare import comparar_carpetas
from .report import write_excel


def _print_summary(result) -> None:
    print(f"BOM: {result.n_bom_archivos} archivos → {result.n_bom_refs} referencias")
    print(f"WI:  {result.n_wi_archivos} archivos → {result.n_wi_refs} referencias")
    print(
        f"Faltan WI: {len(result.faltan)}   "
        f"Completas: {len(result.coinciden)}   "
        f"WI sin BOM: {len(result.sobran)}"
    )
    if result.omitidos_bom:
        print(f"BOM omitidos (coordenadas): {len(result.omitidos_bom)}")
    if result.faltan:
        print("\nFaltan instrucciones:")
        for row in result.faltan:
            nombres = " | ".join(item.name for item in row.boms)
            print(f"  {row.referencia:32}  {nombres}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Comparador_DOC: compara carpetas de BOM e instrucciones (WI)."
    )
    parser.add_argument("--bom", help="Carpeta de archivos BOM (.xls/.xlsx)")
    parser.add_argument("--wi", help="Carpeta de instrucciones (.doc/.docx/.pdf)")
    parser.add_argument("--web", action="store_true", help="Abre la aplicacion local")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("instrucciones_faltantes.xlsx"),
        help="Excel de salida",
    )
    parser.add_argument("--filtro", default="", help="Filtrar referencia")
    parser.add_argument(
        "--prefijos",
        default="",
        help="Prefijos extra a quitar, separados por coma",
    )
    args = parser.parse_args(argv)

    if args.web:
        from .app import main as web_main

        web_main()
        return 0

    if not args.bom or not args.wi:
        parser.error("Indica --bom y --wi, o usa --web")

    from .names import parsear_prefijos_extra

    try:
        result = comparar_carpetas(
            args.bom,
            args.wi,
            prefijos_extra=parsear_prefijos_extra(args.prefijos),
            filtro=args.filtro,
        )
        out = write_excel(result, args.out)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    _print_summary(result)
    print(f"\nEscrito {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
