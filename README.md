# Asignador de casos

Aplicación local en Streamlit para consolidar los archivos de casos, administrar
profesionales y generar un Excel con la hoja `Asignador`, resúmenes y fuentes
Raw.

## Instalación

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecución

```powershell
streamlit run asignador_app.py
```

La tabla persistente se guarda en `profesionales.csv`. Si el archivo no existe,
la aplicación lo crea automáticamente con los profesionales del Excel de
referencia.

El archivo `exported-logs` es opcional. Cuando se carga, la columna `LLEGADA`
se calcula recorriendo las transiciones del caso. Las devoluciones y
reaperturas reinician la llegada cuando el caso vuelve al dibujante. Cuando no
se carga, usa la fecha y hora local de Colombia del momento de generación.

La configuración local permite cargar archivos de hasta 500 MB.
