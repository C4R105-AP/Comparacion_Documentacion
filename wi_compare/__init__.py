"""Comparador_DOC: cruza carpetas de BOM e instrucciones por referencia."""

from .compare import comparar_carpetas
from .models import CompareResult, FileHit, MatchRow

__all__ = ["CompareResult", "FileHit", "MatchRow", "comparar_carpetas"]
