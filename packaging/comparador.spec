# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

PACKAGING = Path(SPECPATH).resolve()
ROOT = PACKAGING.parent
STATIC_SRC = ROOT / "wi_compare" / "static"

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "multipart",
    "python_multipart",
    "openpyxl",
    "tkinter",
    "tkinter.messagebox",
    "tkinter.filedialog",
    *collect_submodules("wi_compare"),
]

excludes = [
    "torch",
    "tensorflow",
    "matplotlib",
    "scipy",
    "IPython",
    "notebook",
    "pytest",
    "sphinx",
    "botocore",
    "boto3",
    "sqlalchemy",
    "PyQt5",
    "PySide2",
    "cv2",
    "sklearn",
    "sympy",
    "numba",
    "numexpr",
    "pandas",
]

a = Analysis(
    [str(PACKAGING / "launch_comparador.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(STATIC_SRC), "static")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Comparador_DOC",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Comparador_DOC",
)
