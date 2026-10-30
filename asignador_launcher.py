from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import asignador_core  # noqa: F401 - garantiza su inclusión en el ejecutable
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from streamlit.web import cli as streamlit_cli


URL_APLICACION = "http://localhost:8501"


def ruta_recurso(nombre: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / nombre


def servidor_activo() -> bool:
    try:
        with urlopen(f"{URL_APLICACION}/_stcore/health", timeout=1) as respuesta:
            return respuesta.status == 200 and respuesta.read().strip() == b"ok"
    except (OSError, URLError):
        return False


def abrir_navegador_cuando_este_listo() -> None:
    for _ in range(120):
        if servidor_activo():
            webbrowser.open(URL_APLICACION)
            return
        time.sleep(0.25)


def main() -> None:
    if servidor_activo():
        webbrowser.open(URL_APLICACION)
        return

    aplicacion = ruta_recurso("asignador_app.py")
    threading.Thread(target=abrir_navegador_cuando_este_listo, daemon=True).start()
    sys.argv = [
        "streamlit",
        "run",
        str(aplicacion),
        "--global.developmentMode=false",
        "--server.address=localhost",
        "--server.port=8501",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--server.maxUploadSize=500",
        "--server.maxMessageSize=500",
        "--browser.gatherUsageStats=false",
    ]
    raise SystemExit(streamlit_cli.main())


if __name__ == "__main__":
    main()
