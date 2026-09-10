from __future__ import annotations

import json
import os
import sys
import tempfile
from io import BytesIO
from pathlib import Path

from fastapi import Body, FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .compare import comparar_listas
from .folder_dialog import pick_folder
from .models import CompareResult, FileRef
from .report import write_excel
from .scan import (
    EXTENSIONES_BOM,
    EXTENSIONES_WI,
    archivos_desde_nombres,
    listar_boms,
    listar_wis,
    partir_boms,
)


def _bundle_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


STATIC = _bundle_dir() / "static"
_TMP = Path(tempfile.gettempdir()) / "comparador_doc"
_TMP.mkdir(exist_ok=True)

app = FastAPI(title="Comparador_DOC")
app.mount("/static", StaticFiles(directory=STATIC), name="static")

STATE: dict = {"result": None, "xlsx": None, "config": {}}


def _config_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    folder = base / "comparador_doc"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "config.json"


def _load_config() -> dict:
    path = _config_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_config(data: dict) -> None:
    STATE["config"] = data
    try:
        _config_path().write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def _as_dir(raw: str) -> Path:
    path = Path(str(raw or "").strip().strip('"'))
    if path.is_file():
        return path.parent
    return path


def _file(item: FileRef) -> dict:
    return {
        "archivo": item.name,
        "subcarpeta": item.subcarpeta,
        "relativo": item.relativo or item.name,
    }


def _row(row) -> dict:
    return {
        "referencia": row.referencia,
        "boms": [item.name for item in row.boms],
        "wis": [item.name for item in row.wis],
        "bom_files": [_file(item) for item in row.boms],
        "wi_files": [_file(item) for item in row.wis],
        "rutas_bom": [item.path for item in row.boms],
        "rutas_wi": [item.path for item in row.wis],
    }


def _hit(hit) -> dict:
    return {"archivo": hit.name, "limpio": hit.limpio, "ruta": hit.path}


def _payload(result: CompareResult) -> dict:
    return {
        "carpeta_bom": result.carpeta_bom,
        "carpeta_wi": result.carpeta_wi,
        "stats": {
            "faltan": len(result.faltan),
            "coinciden": len(result.coinciden),
            "sobran": len(result.sobran),
            "sin_reconocer": len(result.bom_no_reconocidos) + len(result.wi_no_reconocidas),
            "omitidos": len(result.omitidos_bom),
            "n_bom_archivos": result.n_bom_archivos,
            "n_wi_archivos": result.n_wi_archivos,
            "n_bom_refs": result.n_bom_refs,
            "n_wi_refs": result.n_wi_refs,
            "n_bom_obsoletas": result.n_bom_obsoletas,
        },
        "faltan": [_row(r) for r in result.faltan],
        "coinciden": [_row(r) for r in result.coinciden],
        "sobran": [_row(r) for r in result.sobran],
        "bom_no_reconocidos": [_hit(h) for h in result.bom_no_reconocidos],
        "wi_no_reconocidas": [_hit(h) for h in result.wi_no_reconocidas],
        "omitidos_bom": [_hit(h) for h in result.omitidos_bom],
    }


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/config")
def get_config():
    cfg = STATE.get("config") or _load_config()
    STATE["config"] = cfg
    return cfg


@app.post("/api/pick-folder")
def pick_folder_api(payload: dict | None = Body(None)):
    payload = payload or {}
    title = str(payload.get("title") or "Selecciona una carpeta")
    initial = str(payload.get("initial") or "")
    path = pick_folder(title, initial, payload.get("x"), payload.get("y"))
    return {"path": path}


def _lado(path_raw, files, es_bom: bool):
    path_txt = str(path_raw or "").strip()
    if path_txt:
        carpeta = _as_dir(path_txt)
        if carpeta.is_dir():
            if es_bom:
                usar, omitidos = listar_boms(str(carpeta))
                return str(carpeta), usar, omitidos
            return str(carpeta), listar_wis(str(carpeta)), []
    if files:
        if es_bom:
            brutos = archivos_desde_nombres(files, EXTENSIONES_BOM)
            usar, omitidos = partir_boms(brutos)
            return "BOM", usar, omitidos
        return "WI", archivos_desde_nombres(files, EXTENSIONES_WI), []
    return None


@app.post("/api/compare")
def compare(payload: dict | None = Body(None)):
    payload = payload or {}
    lado_bom = _lado(payload.get("bom"), payload.get("bom_files"), True)
    lado_wi = _lado(payload.get("wi"), payload.get("wi_files"), False)
    if not lado_bom or not lado_wi:
        return JSONResponse({"error": "Indica ambas carpetas."}, status_code=400)

    try:
        result = comparar_listas(
            lado_bom[1],
            lado_wi[1],
            lado_bom[2],
            carpeta_bom=lado_bom[0],
            carpeta_wi=lado_wi[0],
            ignorar_mayusculas=True,
        )
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)

    xlsx = _TMP / "instrucciones_faltantes.xlsx"
    write_excel(result, xlsx)
    STATE["result"] = result
    STATE["xlsx"] = str(xlsx)
    _save_config(
        {
            "bom": lado_bom[0] if Path(lado_bom[0]).is_dir() else str(payload.get("bom") or ""),
            "wi": lado_wi[0] if Path(lado_wi[0]).is_dir() else str(payload.get("wi") or ""),
        }
    )
    return _payload(result)


@app.get("/api/download")
def download():
    result = STATE.get("result")
    if result is None:
        return JSONResponse({"error": "Compara primero"}, status_code=400)
    xlsx = Path(STATE.get("xlsx") or (_TMP / "instrucciones_faltantes.xlsx"))
    write_excel(result, xlsx)
    data = xlsx.read_bytes()
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=instrucciones_faltantes.xlsx"},
    )


def _pick_port(start: int = 8770, tries: int = 8) -> int:
    import socket

    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError(f"No hay puerto libre desde {start}")


def _alert(message: str) -> None:
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("Comparador_DOC", message)
        root.destroy()
    except Exception:
        print(message, file=sys.stderr)


def _ensure_stdio() -> None:
    if sys.stdout is not None and sys.stderr is not None:
        return
    log_path = Path(tempfile.gettempdir()) / "comparador_doc.log"
    stream = open(log_path, "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


def main() -> None:
    import multiprocessing
    import webbrowser

    import uvicorn

    multiprocessing.freeze_support()
    _ensure_stdio()
    STATE["config"] = _load_config()
    try:
        port = _pick_port()
    except Exception as exc:
        _alert(str(exc))
        raise SystemExit(1) from exc
    url = f"http://127.0.0.1:{port}"
    webbrowser.open(url)
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"format": "%(levelname)s: %(message)s"},
            "access": {"format": "%(message)s"},
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "class": "logging.StreamHandler",
                "formatter": "access",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "WARNING"},
            "uvicorn.error": {"handlers": ["default"], "level": "WARNING"},
            "uvicorn.access": {
                "handlers": ["access"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }
    try:
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            log_config=log_config,
        )
    except Exception as exc:
        _alert(str(exc))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
