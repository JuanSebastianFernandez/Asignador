import io
import unittest

from openpyxl import Workbook, load_workbook

from asignador_core import (
    COLUMNAS_ASIGNADOR,
    ErrorDatos,
    exportar_excel,
    leer_csv,
    leer_plan_odms,
    procesar_archivos,
    profesionales_por_defecto,
)


def _plan(*filas):
    archivo = io.BytesIO()
    libro = Workbook()
    for fila in filas:
        libro.active.append(fila)
    libro.save(archivo)
    return archivo


class PlanOdmsTests(unittest.TestCase):
    def test_cruce_y_exportacion_del_agp_por_qr(self):
        fuentes = {
            "exported_request_DW": (
                b"request_code;status;process__subprocess;drawing_user_last_name\n"
                b"QR-VIEJO;2.5;Proyectos;\n"
            ),
            "exported_drawing": (
                b"request_code;status;process.subprocess;assigned_draftsman\n"
                b"QR-NUEVO;drawing_request;Proyectos;\n"
                b"QR-SIN-AGP;assigned_draftsman;Proyectos;\n"
                b"QR-FUERA;drawing_review;Proyectos;\n"
            ),
            "exported_request_20": (
                b"request_code;status;process__subprocess;user_assigned_last_name;"
                b"new_fulfillment_process;base_order\n"
                b"QR-20;2.6;Proyectos;;True;\n"
            ),
            "grouped_node_report": b"request_code\nQR-NUEVO\n",
        }
        plan = _plan(
            ("QR", "ODM VALORIZADA", "AGP"),
            (" qr-nuevo ", "ODM-1", "00042"),
            ("QR-20", "ODM-2", 1234),
            ("QR-20", "ODM-2", 1234),
            ("QR-20", "ODM-3", 4567),
            ("QR-VIEJO", "ODM-4", 999),
            ("QR-SIN-AGP", "ODM-5", None),
            ("QR-FUERA", "ODM-6", 99),
        )

        profesionales = profesionales_por_defecto()
        sin_plan, _, _ = procesar_archivos(fuentes, profesionales)
        asignador, resumenes, raw = procesar_archivos(
            fuentes, profesionales, plan_odms=plan
        )

        self.assertEqual(sin_plan.columns.tolist(), COLUMNAS_ASIGNADOR)
        self.assertEqual(asignador["QR"].tolist(), sin_plan["QR"].tolist())
        self.assertEqual(asignador.set_index("QR")["AGP"].to_dict(), {
            "QR-VIEJO": "",
            "QR-NUEVO": "00042",
            "QR-SIN-AGP": "",
            "QR-20": "1234 / 4567",
        })

        excel = exportar_excel(asignador, resumenes, profesionales, raw)
        libro = load_workbook(io.BytesIO(excel), read_only=True)
        try:
            filas = list(libro["Asignador"].values)
        finally:
            libro.close()
        self.assertEqual(filas[0][-1], "AGP")
        self.assertEqual({fila[0]: fila[-1] for fila in filas[1:]}, {
            "QR-VIEJO": None,
            "QR-NUEVO": "00042",
            "QR-SIN-AGP": None,
            "QR-20": "1234 / 4567",
        })

        for tipo in ("exported_request_DW", "exported_request_20"):
            fuentes[tipo] = fuentes[tipo].splitlines(keepends=True)[0]
        con_bandejas_vacias, _, _ = procesar_archivos(
            fuentes, profesionales, plan_odms=plan
        )
        self.assertEqual(con_bandejas_vacias["AGP"].tolist(), ["00042", ""])

    def test_rechaza_un_plan_con_columnas_en_orden_incorrecto(self):
        plan = _plan(("QR", "AGP", "ODM"), ("QR-1", 42, "ODM-1"))
        with self.assertRaisesRegex(ErrorDatos, "QR en A.*AGP en C"):
            leer_plan_odms(plan)

    def test_lee_reporte_pms_si_la_muestra_corta_un_caracter_utf8(self):
        inicio = b'\xef\xbb\xbf"request_code";"observaciones"\n"QR-1";"'
        relleno = b"a" * (199_999 - len(inicio))
        archivo = inicio + relleno + b'\xc3\xa9"\n'

        reporte = leer_csv(archivo)

        self.assertEqual(reporte.loc[0, "request_code"], "QR-1")
        self.assertTrue(reporte.loc[0, "observaciones"].endswith("\u00e9"))
