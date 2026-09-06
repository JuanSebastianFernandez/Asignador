from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd
import streamlit as st

from asignador_core import (
    ARCHIVOS_OBLIGATORIOS,
    ErrorDatos,
    TIPOS_ARCHIVO,
    VERSION_LOGICA_PROCESAMIENTO,
    cargar_profesionales,
    exportar_excel,
    guardar_profesionales,
    identificar_archivos,
    procesar_archivos,
)


RUTA_PROFESIONALES = Path(__file__).with_name("profesionales.csv")
GITHUB_API = "https://api.github.com"


def _leer_secretos_github() -> dict[str, str]:
    try:
        github = st.secrets.get("github", {})
        token = github.get("token", st.secrets.get("GITHUB_TOKEN", ""))
        repo = github.get(
            "repo",
            st.secrets.get("GITHUB_REPO", "JuanSebastianFernandez/Asignador"),
        )
        branch = github.get("branch", st.secrets.get("GITHUB_BRANCH", "main"))
        path = github.get(
            "path",
            st.secrets.get("GITHUB_PROFESIONALES_PATH", "profesionales.csv"),
        )
    except Exception:
        return {}

    config = {
        "token": str(token).strip(),
        "repo": str(repo).strip(),
        "branch": str(branch).strip(),
        "path": str(path).strip(),
    }
    return config if config["token"] and config["repo"] and config["path"] else {}


def _github_request(
    config: dict[str, str],
    method: str,
    url: str,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {config['token']}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "asignador-streamlit",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detalle = exc.read().decode("utf-8", errors="ignore")
        raise ErrorDatos(
            f"GitHub respondió con error {exc.code}. Detalle: {detalle}"
        ) from exc
    except URLError as exc:
        raise ErrorDatos(f"No fue posible conectar con GitHub: {exc}") from exc


def _github_contents_url(config: dict[str, str]) -> str:
    path = quote(config["path"], safe="/")
    repo = quote(config["repo"], safe="/")
    return f"{GITHUB_API}/repos/{repo}/contents/{path}"


def cargar_profesionales_github(config: dict[str, str]) -> tuple[pd.DataFrame, str]:
    url = f"{_github_contents_url(config)}?ref={quote(config['branch'])}"
    contenido = _github_request(config, "GET", url)
    codificado = str(contenido.get("content", "")).replace("\n", "")
    texto_csv = base64.b64decode(codificado).decode("utf-8-sig")
    df = pd.read_csv(io.StringIO(texto_csv), dtype=str, keep_default_na=False)
    sha = str(contenido.get("sha", ""))
    if not sha:
        raise ErrorDatos("GitHub no devolvió el identificador SHA de profesionales.csv.")
    return df, sha


def guardar_profesionales_github(
    df: pd.DataFrame,
    config: dict[str, str],
    sha_actual: str | None,
) -> pd.DataFrame:
    profesionales = guardar_profesionales(df, RUTA_PROFESIONALES)
    buffer = io.StringIO()
    profesionales.to_csv(buffer, index=False, encoding="utf-8")
    contenido = base64.b64encode(buffer.getvalue().encode("utf-8-sig")).decode("ascii")

    payload: dict[str, object] = {
        "message": "Actualizar profesionales desde Streamlit",
        "content": contenido,
        "branch": config["branch"],
    }
    if sha_actual:
        payload["sha"] = sha_actual

    _github_request(config, "PUT", _github_contents_url(config), payload)
    return profesionales


st.set_page_config(
    page_title="Asignador de casos",
    layout="wide",
)

st.title("Asignador de casos")
st.caption(
    "Carga las tres fuentes obligatorias y, opcionalmente, los logs; administra "
    "los profesionales y genera el Excel con trazabilidad completa."
)

if st.session_state.get("version_logica_procesamiento") != VERSION_LOGICA_PROCESAMIENTO:
    st.session_state.pop("resultado_asignador", None)
    st.session_state["version_logica_procesamiento"] = VERSION_LOGICA_PROCESAMIENTO


@st.cache_data(show_spinner=False)
def cargar_tabla_profesionales_local(ruta: str, marca_tiempo: float) -> pd.DataFrame:
    del marca_tiempo
    return cargar_profesionales(ruta)


@st.cache_data(show_spinner=False)
def cargar_tabla_profesionales_remota(
    repo: str,
    branch: str,
    path: str,
    token_marker: str,
) -> tuple[pd.DataFrame, str]:
    del token_marker
    config = _leer_secretos_github()
    if not config:
        raise ErrorDatos("No hay configuración de GitHub para cargar profesionales.")
    config.update({"repo": repo, "branch": branch, "path": path})
    return cargar_profesionales_github(config)


def obtener_profesionales() -> tuple[pd.DataFrame, str | None, dict[str, str]]:
    github_config = _leer_secretos_github()
    if github_config:
        df, sha = cargar_tabla_profesionales_remota(
            github_config["repo"],
            github_config["branch"],
            github_config["path"],
            github_config["token"][-6:],
        )
        guardar_profesionales(df, RUTA_PROFESIONALES)
        return df, sha, github_config

    if not RUTA_PROFESIONALES.exists():
        return cargar_profesionales(RUTA_PROFESIONALES), None, {}
    return (
        cargar_tabla_profesionales_local(
            str(RUTA_PROFESIONALES),
            RUTA_PROFESIONALES.stat().st_mtime,
        ),
        None,
        {},
    )


def mostrar_resumenes(resumenes: dict[str, pd.DataFrame]) -> None:
    st.subheader("Resúmenes")
    izquierda, derecha = st.columns(2)
    with izquierda:
        st.markdown("**Casos por flujo**")
        st.dataframe(resumenes["casos_por_flujo"], hide_index=True, use_container_width=True)
        st.markdown("**Casos por USER**")
        st.dataframe(resumenes["casos_por_user"], hide_index=True, use_container_width=True)
    with derecha:
        st.markdown("**Casos por origen**")
        st.dataframe(resumenes["casos_por_origen"], hide_index=True, use_container_width=True)
        st.markdown("**Elementos por USER**")
        st.dataframe(
            resumenes["elementos_por_user"], hide_index=True, use_container_width=True
        )
    st.markdown("**Posibles PNC**")
    st.dataframe(resumenes["posibles_pnc"], hide_index=True, use_container_width=True)


def mostrar_detalle_posibles_pnc(asignador: pd.DataFrame) -> None:
    posibles_pnc = asignador.loc[asignador["POSIBLE_PNC"].eq("Si")].copy()
    if posibles_pnc.empty:
        st.info("No se detectaron posibles PNC con la lógica actual.")
        return

    columnas = ["QR", "FLUJO", "ORIGEN", "ESTADO", "LLEGADA", "USER"]
    st.markdown("**Detalle de posibles PNC**")
    st.dataframe(
        posibles_pnc[columnas],
        hide_index=True,
        use_container_width=True,
    )


tab_carga, tab_profesionales = st.tabs(
    ["Carga y generación", "Gestión de profesionales"]
)

with tab_profesionales:
    st.subheader("Profesionales")
    st.write(
        "Edite las celdas, agregue filas desde el control de la tabla o marque "
        "`ELIMINAR` y guarde los cambios."
    )
    try:
        profesionales_actuales, profesionales_sha, github_config = (
            obtener_profesionales()
        )
    except ErrorDatos as exc:
        st.error(str(exc))
        profesionales_actuales = pd.DataFrame(columns=["CEDULA", "NOMBRE", "CORREO"])
        profesionales_sha = None
        github_config = {}

    if github_config:
        st.info(
            "Persistencia activa: los cambios se guardarán en GitHub "
            f"`{github_config['repo']}/{github_config['path']}`."
        )
    else:
        st.warning(
            "Persistencia local: en Streamlit Community Cloud los cambios se pueden "
            "perder al reiniciar. Configure los secretos de GitHub para guardarlos."
        )

    profesionales_editor = profesionales_actuales.copy()
    profesionales_editor.insert(0, "ELIMINAR", False)
    profesionales_editados = st.data_editor(
        profesionales_editor,
        hide_index=True,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "ELIMINAR": st.column_config.CheckboxColumn(
                "ELIMINAR",
                help="Marque esta casilla para eliminar el profesional al guardar.",
                default=False,
            ),
            "CEDULA": st.column_config.TextColumn(
                "CEDULA",
                help="Se guarda como texto y se conservan únicamente dígitos.",
            ),
            "NOMBRE": st.column_config.TextColumn("NOMBRE"),
            "CORREO": st.column_config.TextColumn("CORREO"),
        },
        key="editor_profesionales",
    )

    if st.button("Guardar profesionales", type="primary"):
        try:
            para_guardar = profesionales_editados.loc[
                ~profesionales_editados["ELIMINAR"].fillna(False),
                ["CEDULA", "NOMBRE", "CORREO"],
            ]
            if github_config:
                guardados = guardar_profesionales_github(
                    para_guardar,
                    github_config,
                    profesionales_sha,
                )
                cargar_tabla_profesionales_remota.clear()
            else:
                guardados = guardar_profesionales(para_guardar, RUTA_PROFESIONALES)
                cargar_tabla_profesionales_local.clear()
            st.success(f"Se guardaron {len(guardados)} profesionales.")
            st.rerun()
        except ErrorDatos as exc:
            st.error(str(exc))

with tab_carga:
    st.subheader("1. Carga de archivos")
    archivos_cargados = st.file_uploader(
        "Seleccione los tres archivos obligatorios y, si lo tiene, el archivo de logs",
        type=["csv"],
        accept_multiple_files=True,
        help=(
            "La identificación usa la parte fija del nombre; la fecha o número "
            "inicial puede cambiar."
        ),
    )

    encontrados, duplicados, no_reconocidos = identificar_archivos(archivos_cargados)
    columnas_estado = st.columns(4)
    for columna, (tipo, patron) in zip(columnas_estado, TIPOS_ARCHIVO.items()):
        with columna:
            if tipo in encontrados:
                st.success(f"Encontrado\n\n`{encontrados[tipo].name}`")
            elif tipo == "exported_logs":
                st.warning(
                    "Opcional\n\nSin logs se usará la fecha local de Colombia."
                )
            else:
                st.error(f"Faltante\n\n`{patron}`")

    if duplicados:
        detalle = "; ".join(
            f"{TIPOS_ARCHIVO[tipo]}: {', '.join(nombres)}"
            for tipo, nombres in duplicados.items()
        )
        st.error(f"Hay archivos duplicados para la misma fuente: {detalle}")
    if no_reconocidos:
        st.warning("Archivos no reconocidos: " + ", ".join(no_reconocidos))

    st.subheader("2. Generar Asignador")
    puede_generar = (
        ARCHIVOS_OBLIGATORIOS.issubset(encontrados) and not duplicados
    )
    if st.button(
        "Generar Asignador",
        type="primary",
        disabled=not puede_generar,
        use_container_width=True,
    ):
        try:
            profesionales, _, _ = obtener_profesionales()
            with st.status("Procesando archivos...", expanded=True) as estado:
                st.write("Leyendo y validando los CSV.")
                asignador, resumenes, raw_data = procesar_archivos(
                    encontrados, profesionales
                )
                st.write("Construyendo resúmenes y hojas Raw.")
                excel = exportar_excel(
                    asignador, resumenes, profesionales, raw_data
                )
                estado.update(
                    label="Asignador generado correctamente.",
                    state="complete",
                    expanded=False,
                )
            st.session_state["resultado_asignador"] = {
                "asignador": asignador,
                "resumenes": resumenes,
                "excel": excel,
            }
        except ErrorDatos as exc:
            st.error(str(exc))
        except Exception as exc:
            st.error(f"Ocurrió un error inesperado durante el procesamiento: {exc}")

    resultado = st.session_state.get("resultado_asignador")
    if resultado:
        asignador = resultado["asignador"]
        sin_asignar = asignador["USER"].fillna("").eq("").sum()
        total_elementos = int(asignador["ELEMENTOS"].sum())
        posibles_pnc = int(asignador["POSIBLE_PNC"].eq("Si").sum())
        metrica_1, metrica_2, metrica_3, metrica_4 = st.columns(4)
        metrica_1.metric("Casos", f"{len(asignador):,}".replace(",", "."))
        metrica_2.metric("Sin asignar", f"{sin_asignar:,}".replace(",", "."))
        metrica_3.metric(
            "Elementos", f"{total_elementos:,}".replace(",", ".")
        )
        metrica_4.metric("Posibles PNC", f"{posibles_pnc:,}".replace(",", "."))

        st.subheader("Vista previa de Asignador")
        st.dataframe(asignador, hide_index=True, use_container_width=True)
        mostrar_resumenes(resultado["resumenes"])
        mostrar_detalle_posibles_pnc(asignador)
        st.download_button(
            "Descargar Casos_asigna_generado.xlsx",
            data=resultado["excel"],
            file_name="Casos_asigna_generado.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            type="primary",
            use_container_width=True,
        )
