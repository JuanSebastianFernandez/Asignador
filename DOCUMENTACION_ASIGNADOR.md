# Funcionamiento del Asignador de Casos

## 1. Descripción general

El **Asignador de Casos** es una aplicación desarrollada en Python con
Streamlit que consolida información proveniente del sistema PMS para facilitar
la asignación de casos a profesionales.

La aplicación permite:

- Cargar los archivos exportados desde PMS.
- Identificar automáticamente cada fuente por su nombre.
- Separar los casos de flujo viejo, flujo nuevo y flujo 2.0.
- Identificar los casos pendientes de asignación.
- Calcular la cantidad de elementos asociados a cada QR.
- Determinar la fecha de llegada vigente mediante el historial del log.
- Detectar posibles productos no conformes, o posibles PNC.
- Relacionar cédulas con la tabla de profesionales.
- Generar resúmenes operativos.
- Exportar un Excel con el resultado y los datos originales.

La lógica de procesamiento se encuentra principalmente en
`asignador_core.py`, mientras que la interfaz, la carga de archivos y la gestión
de profesionales están en `asignador_app.py`.

## 2. Archivos de entrada

La aplicación reconoce los archivos por la parte fija de su nombre. La fecha o
el número inicial puede cambiar sin afectar la identificación.

| Fuente | Texto utilizado para identificarla | Uso | Obligatorio |
|---|---|---|---:|
| Logs | `exported-logs` | Llegada y posibles PNC | No |
| Nodos | `grouped-node-report` | Cantidad de elementos | Sí |
| Solicitudes DW | `exported-request_DW` | Casos de flujo viejo | Sí |
| Dibujos | `exported-drawing` | Casos de flujo nuevo | Sí |
| Solicitudes generales | `exported-request` | Identificación de Flujo 2.0 | Sí |

La aplicación intenta detectar automáticamente:

- Codificación UTF-8 con o sin BOM.
- Codificación Windows-1252.
- Codificación Latin-1.
- Separadores por coma, punto y coma, tabulación o `|`.

Si se carga más de un archivo correspondiente a la misma fuente, la generación
se bloquea para evitar procesar información ambigua.

## 3. Columnas obligatorias

### `exported-request_DW`

```text
request_code
status
process__subprocess
drawing_user_last_name
```

### `exported-drawing`

```text
request_code
status
process.subprocess
assigned_draftsman
```

### `grouped-node-report`

```text
request_code
```

### `exported-logs`

```text
request_code
initial_state
final_state
date_created
comments
```

### `exported-request` para Flujo 2.0

```text
request_code
status
process__subprocess
user_assigned_last_name
new_fulfillment_process
base_order
```

Si falta una columna, la aplicación informa el archivo afectado, las columnas
faltantes y las columnas disponibles.

## 4. Estados manejados

La aplicación utiliza tres grupos de estados: asignación, devolución y entrega.

| Flujo | Estados de asignación | Estados de devolución | Estado de entrega |
|---|---|---|---|
| Flujo viejo | `2.5`, `2.6` | `2`, `2.6.1` | `2.7` |
| Flujo nuevo | `drawing_request`, `assigned_draftsman` | `verify_formats` | `drawing_review` |
| Flujo 2.0 | `2.5`, `2.6` | `2`, `2.6.1` | `2.7` |

Los estados de asignación determinan los casos que aparecen en la hoja
**Asignador**. Los estados de devolución y entrega se utilizan para reconstruir
la llegada vigente y detectar posibles PNC.

En el flujo viejo, la columna `ESTADO` conserva el texto original recibido en
PMS, por ejemplo:

```text
2.5-Pendiente asignar dibujante
2.6-Dibujante asignado
```

En el flujo nuevo se utiliza el estado normalizado:

```text
drawing_request
assigned_draftsman
```

El filtro numérico exige que el código sea exactamente `2.5` o `2.6`; el estado
`2.6.1` no ingresa al Asignador.

### Identificación de Flujo 2.0

Un registro se clasifica como `Flujo 2.0` cuando cumple simultáneamente:

```text
new_fulfillment_process = True
base_order = vacío
```

Después de identificarlo, solo se incorpora si su estado actual es `2.5` o
`2.6`. La clasificación de Flujo 2.0 tiene prioridad si el mismo QR aparece en
otra fuente.

## 5. Construcción de la hoja Asignador

La tabla final contiene las siguientes columnas:

| Columna | Descripción |
|---|---|
| `QR` | Código único del caso |
| `FLUJO` | `Flujo viejo` o `Flujo nuevo` |
| `ORIGEN` | Subproceso u origen del caso |
| `ELEMENTOS` | Cantidad de elementos asociados al QR |
| `ESTADO` | Estado actual de asignación |
| `LLEGADA` | Fecha y hora de llegada del ciclo vigente |
| `USER` | Profesional responsable |
| `POSIBLE_PNC` | Marca `Si` cuando se detecta un posible PNC |

### 5.1 QR y flujo

Para el flujo viejo, el QR sale de `request_code` en
`exported-request_DW`. Para el flujo nuevo sale de `request_code` en
`exported-drawing`.

La columna `FLUJO` se asigna así:

```text
exported-request_DW -> Flujo viejo
exported-drawing    -> Flujo nuevo
exported-request    -> Flujo 2.0, si cumple True + base_order vacío
```

Las filas con `request_code` vacío se excluyen.

### 5.2 Origen

Para flujo viejo se utiliza `process__subprocess`. Para flujo nuevo se utiliza
`process.subprocess`.

Los valores que contengan alguno de estos textos se convierten en `E1`:

```text
Mayor Impacto
Averias BT
Averías BT
```

La búsqueda ignora mayúsculas, minúsculas y tildes.

### 5.3 Elementos

La aplicación cuenta las filas de `grouped-node-report` cuyo `request_code`
coincida con el QR:

```text
ELEMENTOS = cantidad de filas donde request_code = QR
```

Si el QR no aparece en el reporte de nodos, `ELEMENTOS` queda en `0`.

### 5.4 Usuario del flujo viejo

El usuario se obtiene de `drawing_user_last_name`. PMS normalmente entrega el
nombre con apellidos antes de la coma:

```text
Perez De la Cuadra, Julian Oswaldo
```

La aplicación lo transforma en:

```text
Julian Oswaldo Perez De La Cuadra
```

Si falta la coma, el nombre, los apellidos o el contenido real, `USER` queda
vacío.

### 5.5 Usuario del flujo nuevo

El usuario se obtiene de `assigned_draftsman`. Primero se conservan únicamente
los números de la cédula:

```text
CO1030670518 -> 1030670518
```

Después se busca esa cédula en la tabla de profesionales y se trae el campo
`NOMBRE`. Si la cédula está vacía o no existe, `USER` queda vacío.

### 5.6 Usuario del Flujo 2.0

En estado `2.5`, `USER` queda vacío porque el caso todavía está pendiente de
asignación. En estado `2.6`, el usuario no se toma de `exported-request`, porque
ese campo corresponde a quien tiene la solicitud y no necesariamente al
dibujante.

El dibujante se obtiene del último evento válido del log cuyo estado final sea
`2.6`. La aplicación interpreta comentarios como:

```text
Drawing Assignment: Manuel Fernando Sanchez Mondragón
Drawing Reassignment: Manuel Fernando Sanchez Mondragón → David Andrés Luna Yela
```

En una asignación se toma el nombre después de los dos puntos. En una
reasignación se toma el nombre situado a la derecha de la última flecha. Si no
se carga el log o no existe un comentario válido, `USER` queda vacío.

## 6. Cálculo de la llegada

### 6.1 Cuando no se carga el log

Todos los casos reciben como `LLEGADA` la fecha y hora en que se genera el
Asignador, utilizando la zona horaria local de Colombia.

En este escenario, `POSIBLE_PNC` queda vacío porque no existe historial para
evaluarlo.

### 6.2 Cuando se carga el log

Los eventos se procesan cronológicamente por `request_code`, utilizando:

```text
initial_state
final_state
date_created
```

La aplicación sigue solamente los estados relevantes de asignación, devolución
y entrega. La fecha se establece cuando el caso entra a una bandeja activa y se
reinicia cuando regresa después de haber salido por entrega o devolución.

Ejemplo de continuidad dentro del mismo ciclo:

```text
2.5 -> 2.6
```

La llegada continúa siendo la fecha en que el caso entró a `2.5`.

Ejemplo de una nueva llegada después de una entrega:

```text
2.7 -> 2.6
```

La fecha se reinicia cuando el caso vuelve a `2.6`.

Ejemplo de una nueva llegada después de una devolución:

```text
drawing_review -> verify_formats -> assigned_draftsman
```

La fecha se reinicia cuando el caso vuelve a `assigned_draftsman`.

Un QR puede tener múltiples ciclos. El algoritmo recorre todos los eventos y
conserva la llegada correspondiente al ciclo vigente más reciente.

Si se carga el log, pero un QR no tiene eventos válidos, su `LLEGADA` queda
vacía.

## 7. Detección de posibles PNC

La columna `POSIBLE_PNC` es un prefiltro operativo. No confirma por sí sola que
el caso sea un producto no conforme.

El caso se marca como `Si` cuando vuelve a un estado de asignación y su
antecedente relevante más cercano fue una entrega.

### Flujo viejo

```text
2.7 -> 2.6
Resultado: POSIBLE_PNC = Si
```

### Flujo nuevo

```text
drawing_review -> assigned_draftsman
Resultado: POSIBLE_PNC = Si
```

Los estados de devolución cortan el ciclo anterior. Por ejemplo:

```text
2.7 -> 2.6.1 -> 2.6
Resultado: POSIBLE_PNC vacío
```

```text
drawing_review -> verify_formats -> assigned_draftsman
Resultado: POSIBLE_PNC vacío
```

En estos casos, la devolución reemplaza a la entrega como antecedente relevante
y se interpreta que el ciclo anterior ya fue atendido.

La evaluación se actualiza en cada ciclo, por lo que funciona aunque el caso
haya sido entregado y devuelto varias veces.

## 8. Gestión de profesionales

La tabla de profesionales contiene:

```text
CEDULA
NOMBRE
CORREO
```

La interfaz permite agregar, editar y eliminar profesionales. Antes de guardar:

- La cédula se trata como texto y conserva únicamente dígitos.
- Se eliminan las filas completamente vacías.
- No se permiten cédulas duplicadas.
- No se permite un profesional con nombre pero sin cédula.
- El correo se guarda y se exporta, pero no participa en la asignación.

En la aplicación instalada, la tabla se guarda en:

```text
%LOCALAPPDATA%\Asignador\profesionales.csv
```

En Streamlit Community Cloud puede utilizarse persistencia en GitHub mediante
los secretos configurados para el repositorio.

## 9. Resúmenes

La aplicación genera las siguientes tablas:

1. Casos por `FLUJO` y `ESTADO`.
2. Casos por `ORIGEN` y `ESTADO`.
3. Casos por `USER` y `ESTADO`.
4. Suma de `ELEMENTOS` por `USER` y `ESTADO`.
5. Posibles PNC por `FLUJO`, `ORIGEN` y `USER`.

Los casos cuyo `USER` está vacío aparecen como `Sin asignar` únicamente en los
resúmenes. En la hoja **Asignador**, la celda permanece vacía.

## 10. Información mostrada en la aplicación

Después de generar el Asignador, la interfaz presenta:

- Cantidad total de casos.
- Cantidad de casos sin asignar.
- Suma total de elementos.
- Cantidad de posibles PNC.
- Vista previa completa del Asignador.
- Tablas resumen.
- Detalle de los QR marcados como posibles PNC.
- Botón para descargar el Excel final.

## 11. Excel final

El archivo generado se llama:

```text
Casos_asigna_generado.xlsx
```

Contiene las siguientes hojas:

```text
Asignador
Resumen
Profesionales
Raw_exported_logs
Raw_grouped_node_report
Raw_exported_request_DW
Raw_exported_drawing
Raw_exported_request_20
```

### Asignador

Contiene el resultado final procesado y listo para apoyar la asignación.

### Resumen

Contiene las cinco tablas de consolidación operativa.

### Profesionales

Contiene la tabla vigente utilizada para cruzar las cédulas.

### Hojas Raw

Conservan los datos originales cargados para permitir trazabilidad. Si no se
carga el archivo de logs, `Raw_exported_logs` se crea vacía con sus encabezados.

Si una fuente supera el límite de filas permitido por Excel, la aplicación la
divide en varias hojas Raw numeradas.

## 12. Consideraciones técnicas actuales

- Los QR no se eliminan por duplicado. Si una fuente contiene varias filas
  seleccionadas para el mismo QR, todas aparecen en el Asignador.
- Los resúmenes cuentan filas de la tabla, no necesariamente QR únicos.
- `POSIBLE_PNC` depende de la calidad y continuidad del archivo de logs.
- Si no existe log, no es posible detectar posibles PNC.
- La marca PNC debe ser revisada por el coordinador antes de tomar una decisión.
- La fecha del log se convierte a Colombia cuando contiene información de zona
  horaria. Una fecha sin zona horaria se interpreta con el valor recibido.

## 13. Flujo general del procesamiento

```text
Carga de CSV
    |
    v
Identificación automática de fuentes
    |
    v
Validación de archivos y columnas
    |
    v
Filtrado de estados de asignación
    |
    v
Construcción de flujo viejo y flujo nuevo
    |
    v
Cálculo de ORIGEN, ELEMENTOS y USER
    |
    v
Cálculo de LLEGADA y POSIBLE_PNC
    |
    v
Construcción de resúmenes
    |
    v
Vista previa en Streamlit
    |
    v
Exportación de Casos_asigna_generado.xlsx
```
