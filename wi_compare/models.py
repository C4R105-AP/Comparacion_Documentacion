from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FileRef:
    path: str
    name: str
    stem: str = ""
    subcarpeta: bool = False
    relativo: str = ""


@dataclass
class FileHit:
    path: str
    name: str
    limpio: str = ""


@dataclass
class MatchRow:
    referencia: str
    boms: list[FileRef] = field(default_factory=list)
    wis: list[FileRef] = field(default_factory=list)


@dataclass
class CompareResult:
    carpeta_bom: str
    carpeta_wi: str
    faltan: list[MatchRow]
    coinciden: list[MatchRow]
    sobran: list[MatchRow]
    bom_no_reconocidos: list[FileHit]
    wi_no_reconocidas: list[FileHit]
    omitidos_bom: list[FileHit]
    n_bom_archivos: int
    n_wi_archivos: int
    n_bom_refs: int
    n_wi_refs: int
    n_bom_obsoletas: int = 0
