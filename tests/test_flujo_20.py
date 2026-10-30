from __future__ import annotations

import unittest

import pandas as pd

from asignador_core import (
    construir_asignador,
    identificar_archivos,
    profesionales_por_defecto,
)


def _fuentes_vacias() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    flujo_viejo = pd.DataFrame(
        columns=[
            "request_code",
            "status",
            "process__subprocess",
            "drawing_user_last_name",
        ]
    )
    flujo_nuevo = pd.DataFrame(
        columns=[
            "request_code",
            "status",
            "process.subprocess",
            "assigned_draftsman",
        ]
    )
    nodos = pd.DataFrame(columns=["request_code"])
    return flujo_viejo, flujo_nuevo, nodos


class Flujo20Tests(unittest.TestCase):
    def test_identifica_exported_request_sin_confundir_request_dw(self) -> None:
        encontrados, duplicados, no_reconocidos = identificar_archivos(
            [
                "1793187278-exported-request_DW.csv",
                "20261028-exported-request.csv",
            ]
        )

        self.assertEqual(
            encontrados["exported_request_DW"],
            "1793187278-exported-request_DW.csv",
        )
        self.assertEqual(
            encontrados["exported_request_20"],
            "20261028-exported-request.csv",
        )
        self.assertFalse(duplicados)
        self.assertFalse(no_reconocidos)

    def test_solo_incluye_true_sin_base_order_y_estados_25_26(self) -> None:
        flujo_viejo, flujo_nuevo, nodos = _fuentes_vacias()
        request = pd.DataFrame(
            [
                ["QR-25", "2.5-Enviado a dibujo", "PQRs", "Coordinador, Ana", "True", ""],
                ["QR-26", "2.6-Dibujante asignado", "PQRs", "Perez, Juan", "true", ""],
                ["QR-261", "2.6.1-Devuelto", "PQRs", "Perez, Juan", "True", ""],
                ["QR-BASE", "2.5-Enviado a dibujo", "PQRs", "", "True", "123"],
                ["QR-FALSE", "2.5-Enviado a dibujo", "PQRs", "", "False", ""],
            ],
            columns=[
                "request_code",
                "status",
                "process__subprocess",
                "user_assigned_last_name",
                "new_fulfillment_process",
                "base_order",
            ],
        )

        resultado = construir_asignador(
            flujo_viejo,
            flujo_nuevo,
            request,
            nodos,
            None,
            profesionales_por_defecto(),
        )

        self.assertEqual(resultado["QR"].tolist(), ["QR-25", "QR-26"])
        self.assertEqual(resultado["FLUJO"].tolist(), ["Flujo 2.0", "Flujo 2.0"])
        self.assertEqual(resultado["USER"].tolist(), ["", ""])

    def test_entrega_directa_marca_pnc_y_devolucion_corta_el_ciclo(self) -> None:
        flujo_viejo, flujo_nuevo, nodos = _fuentes_vacias()
        request = pd.DataFrame(
            [
                ["QR-PNC", "2.6-Dibujante asignado", "PQRs", "Perez, Juan", "True", ""],
                ["QR-DEV", "2.6-Dibujante asignado", "PQRs", "Lopez, Maria", "True", ""],
            ],
            columns=[
                "request_code",
                "status",
                "process__subprocess",
                "user_assigned_last_name",
                "new_fulfillment_process",
                "base_order",
            ],
        )
        logs = pd.DataFrame(
            [
                ["QR-PNC", "2.7", "2.6", "2026-10-28 08:00:00", "Drawing Assignment: Ana Perez"],
                ["QR-DEV", "2.7", "2.6.1", "2026-10-28 08:00:00", ""],
                ["QR-DEV", "2.6.1", "2.6", "2026-10-28 09:00:00", "Drawing Assignment: Luis Lopez"],
            ],
            columns=[
                "request_code",
                "initial_state",
                "final_state",
                "date_created",
                "comments",
            ],
        )

        resultado = construir_asignador(
            flujo_viejo,
            flujo_nuevo,
            request,
            nodos,
            logs,
            profesionales_por_defecto(),
        ).set_index("QR")

        self.assertEqual(resultado.loc["QR-PNC", "POSIBLE_PNC"], "Si")
        self.assertEqual(resultado.loc["QR-PNC", "USER"], "Ana Perez")
        self.assertEqual(resultado.loc["QR-DEV", "POSIBLE_PNC"], "")
        self.assertEqual(resultado.loc["QR-DEV", "USER"], "Luis Lopez")
        self.assertEqual(
            resultado.loc["QR-DEV", "LLEGADA"],
            pd.Timestamp("2026-10-28 09:00:00"),
        )

    def test_usa_el_ultimo_dibujante_de_una_reasignacion(self) -> None:
        flujo_viejo, flujo_nuevo, nodos = _fuentes_vacias()
        request = pd.DataFrame(
            [["QR-1", "2.6-Dibujante asignado", "PQRs", "Usuario incorrecto", "True", ""]],
            columns=[
                "request_code",
                "status",
                "process__subprocess",
                "user_assigned_last_name",
                "new_fulfillment_process",
                "base_order",
            ],
        )
        logs = pd.DataFrame(
            [
                ["QR-1", "2.5", "2.6", "2026-10-28 08:00:00", "Drawing Assignment: Manuel Sanchez"],
                ["QR-1", "2.6", "2.6", "2026-10-28 09:00:00", "Drawing Reassignment: Manuel Sanchez → David Andrés Luna Yela"],
            ],
            columns=[
                "request_code",
                "initial_state",
                "final_state",
                "date_created",
                "comments",
            ],
        )

        resultado = construir_asignador(
            flujo_viejo,
            flujo_nuevo,
            request,
            nodos,
            logs,
            profesionales_por_defecto(),
        )

        self.assertEqual(resultado.loc[0, "USER"], "David Andrés Luna Yela")


if __name__ == "__main__":
    unittest.main()
