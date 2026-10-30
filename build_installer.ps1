param(
    [switch]$OmitirDependencias
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $raiz

$python = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "Creando el entorno virtual..."
    py -3.11 -m venv .venv
}

if (-not $OmitirDependencias) {
    Write-Host "Instalando dependencias de compilacion..."
    & $python -m pip install -r requirements-build.txt
}

Write-Host "Construyendo la aplicacion..."
& $python -m PyInstaller --noconfirm --clean Asignador.spec

$candidatosInno = @(
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
)
$iscc = $candidatosInno | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $iscc) {
    throw "No se encontro Inno Setup 6. Instalelo con: winget install JRSoftware.InnoSetup"
}

Write-Host "Creando el instalador..."
& $iscc "installer\Asignador.iss"

$resultado = Join-Path $raiz "installer\output\AsignadorCasos-Setup.exe"
Write-Host "Instalador listo: $resultado"
