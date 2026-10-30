# Asignador de casos

Aplicación local en Streamlit para consolidar los archivos de casos, administrar
profesionales y generar un Excel con la hoja `Asignador`, resúmenes y fuentes
Raw.

La aplicación clasifica casos de `Flujo viejo`, `Flujo nuevo` y `Flujo 2.0`.
El Flujo 2.0 se identifica en `exported-request` cuando
`new_fulfillment_process` es `True` y `base_order` está vacío. Solo ingresan al
Asignador los casos que se encuentran en estado `2.5` o `2.6`.
Los casos `2.5` quedan sin usuario. Para los casos `2.6`, el dibujante se obtiene
del último comentario `Drawing Assignment` o `Drawing Reassignment` del log.

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

Si se carga `exported-logs`, el Asignador también agrega la columna
`POSIBLE_PNC`. Esta marca queda en `Si` cuando el historial muestra que el caso
ya había sido entregado (`2.7` en flujo viejo o `drawing_review` en flujo nuevo)
y luego volvió a una bandeja de asignación (`2.5`/`2.6` o
`drawing_request`/`assigned_draftsman`). La marca sirve como prefiltro para
revisión del coordinador; no reemplaza la validación final del PNC.
Si antes del reingreso aparece una devolución (`2`, `2.6.1` o
`verify_formats`), el caso no se marca como posible PNC porque esa devolución
corta el ciclo anterior.

La configuración local permite cargar archivos de hasta 500 MB.

## Instalador para Windows

El proyecto incluye una compilación para Windows que no requiere Python en el
equipo de destino. Para crearla:

1. Instale Inno Setup 6 una sola vez:

   ```powershell
   winget install JRSoftware.InnoSetup
   ```

2. Desde la raíz del proyecto ejecute:

   ```powershell
   .\build_installer.ps1
   ```

El instalador se genera en
`installer\output\AsignadorCasos-Setup.exe`. Ese es el único archivo que debe
entregarse al usuario final. Al instalarlo se crea un acceso en el menú Inicio y
se ofrece crear otro en el escritorio. La app se abre en el navegador y conserva
su tabla de profesionales en `%LOCALAPPDATA%\Asignador\profesionales.csv`, por
lo que una actualización o reinstalación no borra los cambios del usuario.
