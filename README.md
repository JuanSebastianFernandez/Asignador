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

## Persistencia de profesionales en Streamlit Cloud

En Streamlit Community Cloud el sistema de archivos es temporal. Para que los
cambios hechos desde la tabla de profesionales no se pierdan, configure un token
de GitHub en **App settings > Secrets**:

```toml
[github]
token = "PEGUE_AQUI_SU_TOKEN_DE_GITHUB"
repo = "JuanSebastianFernandez/Asignador"
branch = "main"
path = "profesionales.csv"
```

El token debe tener permiso de lectura y escritura de **Contents** sobre este
repositorio. Cuando la persistencia está activa, cada guardado actualiza
`profesionales.csv` en GitHub.

El archivo `exported-logs` es opcional. Cuando se carga, la columna `LLEGADA`
se calcula recorriendo las transiciones del caso. Las devoluciones y
reaperturas reinician la llegada cuando el caso vuelve al dibujante. Cuando no
se carga, usa la fecha y hora local de Colombia del momento de generación.

La configuración local permite cargar archivos de hasta 500 MB.
