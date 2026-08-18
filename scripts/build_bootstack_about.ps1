param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"
$specFile = Join-Path $projectRoot "SmartPrice-Bootstack-About.spec"
$distDir = Join-Path $projectRoot "dist\bootstack-about"
$workDir = Join-Path $projectRoot "build\bootstack-about"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "No se encontro el entorno de 64 bits: $pythonExe"
}

if ($Clean) {
    if (Test-Path -LiteralPath $distDir) {
        Remove-Item -LiteralPath $distDir -Recurse -Force
    }
    if (Test-Path -LiteralPath $workDir) {
        Remove-Item -LiteralPath $workDir -Recurse -Force
    }
}

& $pythonExe -c "import struct, bootstack, PyInstaller; assert struct.calcsize('P') * 8 == 64; assert bootstack.__version__ == '0.1.6'"
if ($LASTEXITCODE -ne 0) {
    throw "El entorno no cumple Python 64-bit + Bootstack 0.1.6."
}

& $pythonExe -m PyInstaller `
    --noconfirm `
    --distpath $distDir `
    --workpath $workDir `
    $specFile
if ($LASTEXITCODE -ne 0) {
    throw "Fallo el build experimental Bootstack."
}

$exePath = Join-Path $distDir "SmartPrice-Bootstack-About.exe"
if (-not (Test-Path -LiteralPath $exePath)) {
    throw "PyInstaller finalizo sin generar $exePath"
}

Write-Host "BUILD_BOOTSTACK_ABOUT_OK: $exePath"
