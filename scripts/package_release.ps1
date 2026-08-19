param(
    [string]$Version = "",
    [string]$ReleaseName = "SmartPrice",
    [string]$SourceDir = "releases\\SmartPrice",
    [string]$OutputDir = "releases"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if ([string]::IsNullOrWhiteSpace($Version)) {
    $manifestPath = Join-Path $Root "VERSION_MANIFEST.json"
    if (Test-Path $manifestPath) {
        $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
        $Version = [string]$manifest.app.version
    }
}

if ([string]::IsNullOrWhiteSpace($Version)) {
    throw "No se pudo resolver la version. Pasar -Version o actualizar VERSION_MANIFEST.json."
}

if ([System.IO.Path]::IsPathRooted($SourceDir)) {
    $sourcePath = $SourceDir
} else {
    $sourcePath = Join-Path $Root $SourceDir
}
if (-not (Test-Path $sourcePath)) {
    throw "No existe la carpeta a empaquetar: $sourcePath"
}

if ([System.IO.Path]::IsPathRooted($OutputDir)) {
    $outputPath = $OutputDir
} else {
    $outputPath = Join-Path $Root $OutputDir
}
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

$zipName = "${ReleaseName}_v${Version}.zip"
$zipPath = Join-Path $outputPath $zipName
if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

$tempZip = Join-Path $env:TEMP $zipName
if (Test-Path $tempZip) {
    Remove-Item -LiteralPath $tempZip -Force
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $sourcePath,
    $tempZip,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $true
)
Move-Item -LiteralPath $tempZip -Destination $zipPath -Force

$hashValue = $null
if (Get-Command Get-FileHash -ErrorAction SilentlyContinue) {
    $hashValue = (Get-FileHash -Algorithm SHA256 -Path $zipPath).Hash
} else {
    $stream = $null
    try {
        $stream = [System.IO.File]::OpenRead($zipPath)
        $sha256 = [System.Security.Cryptography.SHA256]::Create()
        try {
            $hashBytes = $sha256.ComputeHash($stream)
            $hashValue = ([System.BitConverter]::ToString($hashBytes)).Replace("-", "")
        } finally {
            $sha256.Dispose()
        }
    } finally {
        if ($stream) {
            $stream.Dispose()
        }
    }
}

if ([string]::IsNullOrWhiteSpace($hashValue)) {
    throw "No se pudo calcular el SHA256 para $zipPath"
}

$hashPath = "$zipPath.sha256.txt"
"$hashValue  $zipName" | Set-Content -Path $hashPath -Encoding ASCII

Write-Host "ZIP creado: $zipPath"
Write-Host "SHA256: $hashValue"
