from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


streamlit_datas = collect_data_files("streamlit") + copy_metadata("streamlit")
streamlit_hiddenimports = collect_submodules("streamlit")


a = Analysis(
    ["asignador_launcher.py"],
    pathex=[],
    binaries=[],
    datas=streamlit_datas
    + [
        ("asignador_app.py", "."),
        ("profesionales.csv", "."),
        (".streamlit/config.toml", ".streamlit"),
    ],
    hiddenimports=streamlit_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "notebook", "IPython", "tkinter"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Asignador",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Asignador",
)
