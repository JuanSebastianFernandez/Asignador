from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from asignador_core import (
    ARCHIVOS_OBLIGATORIOS,
    ErrorDatos,
    TIPOS_ARCHIVO,
    cargar_profesionales,
    exportar_excel,
    guardar_profesionales,
    identificar_archivos,
    procesar_archivos,
)


RUTA_PROFESIONALES = Path(__file__).with_name("profesionales.csv")


st.set_page_config(
    page_title="Asignador de casos",
    layout="wide",
)

st.title("Asignador de casos")
st.caption(
    "Carga las tres fuentes obligatorias y, opcionalmente, los logs; administra "
    "los profesionales y genera el Excel con trazabilidad completa."
)


@st.cache_data(show_spinner=False)
def cargar_tabla_profesionales(ruta: str, marca_tiempo: float) -> pd.DataFrame:
    del marca_tiempo
    return cargar_profesionales(ruta)


def obtener_profesionales() -> pd.DataFrame:
    if not RUTA_PROFESIONALES.exists():
        return cargar_profesionales(RUTA_PROFESIONALES)
    return cargar_tabla_profesionales(
        str(RUTA_PROFESIONALES), RUTA_PROFESIONALES.stat().st_mtime
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
        profesionales_actuales = obtener_profesionales()
    except ErrorDatos as exc:
        st.error(str(exc))
        profesionales_actuales = pd.DataFrame(columns=["CEDULA", "NOMBRE", "CORREO"])

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
            guardados = guardar_profesionales(para_guardar, RUTA_PROFESIONALES)
            cargar_tabla_profesionales.clear()
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
            profesionales = obtener_profesionales()
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
        metrica_1, metrica_2, metrica_3 = st.columns(3)
        metrica_1.metric("Casos", f"{len(asignador):,}".replace(",", "."))
        metrica_2.metric("Sin asignar", f"{sin_asignar:,}".replace(",", "."))
        metrica_3.metric(
            "Elementos", f"{total_elementos:,}".replace(",", ".")
        )

        st.subheader("Vista previa de Asignador")
        st.dataframe(asignador, hide_index=True, use_container_width=True)
        mostrar_resumenes(resultado["resumenes"])
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
