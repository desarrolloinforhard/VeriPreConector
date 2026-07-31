param(
    [string]$ConfigPath = "build\auto_py_to_exe.refactor.json",
    [string]$Version = "",
    [string]$ReleaseName = "SmartPrice",
    [string]$DistDir = "releases",
    [string]$PythonPath = "",
    [switch]$SkipPackage,
    [switch]$NoClean,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

function Add-FlagArg {
    param([System.Collections.Generic.List[string]]$ArgsList, [string]$Flag, [bool]$Enabled)
    if ($Enabled) { $ArgsList.Add($Flag) }
}

function Add-ValueArg {
    param([System.Collections.Generic.List[string]]$ArgsList, [string]$Flag, [string]$Value)
    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        $ArgsList.Add($Flag)
        $ArgsList.Add($Value)
    }
}

function Resolve-ProjectPath {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $Value
    }

    if ([System.IO.Path]::IsPathRooted($Value)) {
        return $Value
    }

    return (Join-Path $Root $Value)
}

function Resolve-AddDataValue {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $Value
    }

    $parts = $Value -split ';', 2
    if ($parts.Count -ne 2) {
        return (Resolve-ProjectPath $Value)
    }

    $source = Resolve-ProjectPath $parts[0]
    $target = $parts[1]
    return "$source;$target"
}

function Resolve-BuildPython {
    param([string]$RequestedPythonPath)

    $candidates = [System.Collections.Generic.List[string]]::new()
    if (-not [string]::IsNullOrWhiteSpace($RequestedPythonPath)) {
        $candidates.Add($RequestedPythonPath)
    }
    if (-not [string]::IsNullOrWhiteSpace($env:VIRTUAL_ENV)) {
        $candidates.Add((Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"))
    }
    $candidates.Add((Join-Path $Root ".venv\Scripts\python.exe"))
    $candidates.Add((Join-Path $Root "..\venv_VeriPre_Connector\Scripts\python.exe"))
    $candidates.Add((Join-Path $Root "..\..\venv_VeriPre_Connector\Scripts\python.exe"))

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $pythonCommand) {
        return $pythonCommand.Source
    }

    throw "No se encontro Python para compilar. Active el venv o pase -PythonPath."
}

function Initialize-TclTkEnvironment {
    param([string]$PythonExe)

    $basePrefix = (& $PythonExe -c "import sys; print(sys.base_prefix)" 2>$null | Select-Object -First 1).Trim()
    if ([string]::IsNullOrWhiteSpace($basePrefix)) {
        Write-Host "No se pudo resolver sys.base_prefix para Tcl/Tk."
        return
    }

    $tclRoot = Join-Path $basePrefix "tcl"
    if (-not (Test-Path $tclRoot)) {
        Write-Host "No existe directorio Tcl raiz: $tclRoot"
        return
    }

    $tclDir = Get-ChildItem -Path $tclRoot -Directory -Filter "tcl*" -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName "init.tcl") } |
        Sort-Object Name -Descending |
        Select-Object -First 1
    $tkDir = Get-ChildItem -Path $tclRoot -Directory -Filter "tk*" -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending |
        Select-Object -First 1
    $tclModuleDir = Get-ChildItem -Path $tclRoot -Directory -Filter "tcl8" -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if ($null -ne $tclDir) {
        $env:TCL_LIBRARY = $tclDir.FullName
    }
    if ($null -ne $tkDir) {
        $env:TK_LIBRARY = $tkDir.FullName
    }
    if ($null -ne $tclModuleDir) {
        $script:TclModuleDir = $tclModuleDir.FullName
        $env:TCLLIBPATH = $tclModuleDir.FullName
    } else {
        $script:TclModuleDir = $null
    }

    Write-Host "TCL_LIBRARY=$($env:TCL_LIBRARY)"
    Write-Host "TK_LIBRARY=$($env:TK_LIBRARY)"
    Write-Host "TCLLIBPATH=$($env:TCLLIBPATH)"
}

function Add-TclTkDataArgs {
    param([System.Collections.Generic.List[string]]$ArgsList)

    if (-not [string]::IsNullOrWhiteSpace($env:TCL_LIBRARY) -and (Test-Path $env:TCL_LIBRARY)) {
        $ArgsList.Add("--add-data")
        $ArgsList.Add("$($env:TCL_LIBRARY);_tcl_data")
    }

    if (-not [string]::IsNullOrWhiteSpace($env:TK_LIBRARY) -and (Test-Path $env:TK_LIBRARY)) {
        $ArgsList.Add("--add-data")
        $ArgsList.Add("$($env:TK_LIBRARY);_tk_data")
    }

    if (-not [string]::IsNullOrWhiteSpace($script:TclModuleDir) -and (Test-Path $script:TclModuleDir)) {
        $ArgsList.Add("--add-data")
        $ArgsList.Add("$($script:TclModuleDir);tcl8")
    }
}

function Resolve-VlcRuntimePath {
    $candidates = @(
        $env:VLC_DIR,
        "C:\Program Files\VideoLAN\VLC",
        "C:\Program Files (x86)\VideoLAN\VLC"
    ) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }

    foreach ($candidate in $candidates) {
        if ((Test-Path $candidate) -and (Test-Path (Join-Path $candidate "libvlc.dll"))) {
            return (Resolve-Path $candidate).Path
        }
    }

    return $null
}

function Add-VlcRuntimeArgs {
    param([System.Collections.Generic.List[string]]$ArgsList)

    $vlcRoot = Resolve-VlcRuntimePath
    if ([string]::IsNullOrWhiteSpace($vlcRoot)) {
        Write-Warning @"
No se encontro runtime local de VLC para adjuntar al build.
Se buscó en:
- VLC_DIR
- C:\Program Files\VideoLAN\VLC
- C:\Program Files (x86)\VideoLAN\VLC

La app compilada puede fallar en maquinas donde VLC no este instalado.
"@
        return
    }

    Write-Host "VLC runtime detectado: $vlcRoot"

    $binaryFiles = @(
        "libvlc.dll",
        "libvlccore.dll"
    )

    foreach ($binaryFile in $binaryFiles) {
        $fullPath = Join-Path $vlcRoot $binaryFile
        if (Test-Path $fullPath) {
            $ArgsList.Add("--add-binary")
            $ArgsList.Add("$fullPath;.")
        }
    }

    $dataDirs = @(
        "plugins",
        "lua",
        "locale",
        "hrtfs"
    )

    foreach ($dataDir in $dataDirs) {
        $fullPath = Join-Path $vlcRoot $dataDir
        if (Test-Path $fullPath) {
            $ArgsList.Add("--add-data")
            $ArgsList.Add("$fullPath;$dataDir")
        }
    }
}

function Test-BuildPython {
    param([string]$PythonExe)

    $requiredModules = @(
        "PyInstaller",
        "requests",
        "ttkbootstrap",
        "PIL",
        "pypyodbc",
        "pystray",
        "plyer",
        "customtkinter",
        "cv2",
        "vlc"
    )

    $modulesLiteral = ($requiredModules | ForEach-Object { "'$_'" }) -join ","
    $checkCode = "import importlib, sys; mods=[$modulesLiteral]; [importlib.import_module(m) for m in mods]; print(sys.executable)"
    $output = & $PythonExe -c $checkCode 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "El Python de build no tiene todas las dependencias necesarias:`nPython: $PythonExe`n$output"
    }

    Write-Host "Python de build: $PythonExe"
}

function Test-TkinterRuntime {
    param([string]$PythonExe)

    $checkCode = @'
import os
import sys
import traceback

try:
    import tkinter as tk
    root = tk.Tk()
    patch = root.tk.eval("info patchlevel")
    root.destroy()
    print(f"TK_OK|{patch}")
except Exception as exc:
    print("TK_FAIL")
    print(f"PYTHON={sys.executable}")
    print(f"BASE_PREFIX={sys.base_prefix}")
    print(f"TCL_LIBRARY={os.environ.get('TCL_LIBRARY', '')}")
    print(f"TK_LIBRARY={os.environ.get('TK_LIBRARY', '')}")
    traceback.print_exc()
    raise SystemExit(1)
'@

    $tempFile = [System.IO.Path]::GetTempFileName()
    try {
        $tempPy = [System.IO.Path]::ChangeExtension($tempFile, ".py")
        Move-Item -LiteralPath $tempFile -Destination $tempPy -Force
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($tempPy, $checkCode, $utf8NoBom)

        $previousErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $output = & $PythonExe $tempPy 2>&1
        $ErrorActionPreference = $previousErrorActionPreference
        if ($LASTEXITCODE -ne 0) {
            Write-Warning @"
El runtime Tkinter/Tcl-Tk del Python de build no paso la validacion directa.

Python de build: $PythonExe

Salida:
$output

Recomendacion:
1. Reparar o reinstalar la instalacion de Python base que usa el venv.
2. O recrear el venv desde un Python que tenga tkinter funcional.
3. Luego volver a ejecutar este script.
"@
            return
        }

        $okLine = $output | Where-Object { $_ -like "TK_OK|*" } | Select-Object -First 1
        if ($null -ne $okLine) {
            $patch = $okLine.ToString().Split('|', 2)[1]
            Write-Host "Tkinter OK: Tcl/Tk $patch"
        } else {
            Write-Host "Tkinter OK."
        }
    } finally {
        if (Test-Path $tempPy) {
            Remove-Item -LiteralPath $tempPy -Force -ErrorAction SilentlyContinue
        }
    }
}

function Convert-VersionParts {
    param([string]$VersionText)

    $parts = @($VersionText.Split('.') | ForEach-Object {
        $digits = [regex]::Match($_, '\d+').Value
        if ([string]::IsNullOrWhiteSpace($digits)) { 0 } else { [int]$digits }
    })

    while ($parts.Count -lt 4) { $parts += 0 }
    return $parts[0..3]
}

function Escape-VersionString {
    param([string]$Value)
    if ($null -eq $Value) { return "" }
    return $Value.Replace('\', '\\').Replace('"', '\"')
}

function Write-WindowsVersionInfo {
    param(
        [string]$Path,
        [string]$AppName,
        [string]$CompanyName,
        [string]$Description,
        [string]$VersionText,
        [string]$OriginalFilename
    )

    $versionParts = Convert-VersionParts $VersionText
    $fileVersionTuple = "{0}, {1}, {2}, {3}" -f $versionParts[0], $versionParts[1], $versionParts[2], $versionParts[3]
    $appNameEsc = Escape-VersionString $AppName
    $companyEsc = Escape-VersionString $CompanyName
    $descriptionEsc = Escape-VersionString $Description
    $versionEsc = Escape-VersionString $VersionText
    $originalFilenameEsc = Escape-VersionString $OriginalFilename

    $content = @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($fileVersionTuple),
    prodvers=($fileVersionTuple),
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          "040904B0",
          [
            StringStruct("CompanyName", "$companyEsc"),
            StringStruct("FileDescription", "$descriptionEsc"),
            StringStruct("FileVersion", "$versionEsc"),
            StringStruct("InternalName", "$appNameEsc"),
            StringStruct("OriginalFilename", "$originalFilenameEsc"),
            StringStruct("ProductName", "$appNameEsc"),
            StringStruct("ProductVersion", "$versionEsc")
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct("Translation", [1033, 1200])])
  ]
)
"@

    $targetDir = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($targetDir)) {
        New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $content, $utf8NoBom)
}

$manifestPath = Join-Path $Root "VERSION_MANIFEST.json"
if (-not (Test-Path $manifestPath)) {
    throw "No existe VERSION_MANIFEST.json en $Root"
}

$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json

if ([string]::IsNullOrWhiteSpace($Version)) {
    $Version = [string]$manifest.app.version
}
if ([string]::IsNullOrWhiteSpace($Version)) {
    throw "No se pudo resolver la version. Actualice VERSION_MANIFEST.json o pase -Version."
}

$appName = [string]$manifest.app.name
$companyName = [string]$manifest.app.company
$description = [string]$manifest.app.description
$originalFilename = [string]$manifest.app.original_filename

if ([string]::IsNullOrWhiteSpace($appName)) { $appName = $ReleaseName }
if ([string]::IsNullOrWhiteSpace($companyName)) { $companyName = "Inforhard Servicios S.R.L" }
if ([string]::IsNullOrWhiteSpace($description)) { $description = $ReleaseName }
if ([string]::IsNullOrWhiteSpace($originalFilename)) { $originalFilename = "$appName.exe" }

$versionFilePath = Join-Path $Root "build\windows_version_info.txt"
if (-not [string]::IsNullOrWhiteSpace([string]$manifest.build.version_file)) {
    $versionFileFromManifest = [string]$manifest.build.version_file
    if ([System.IO.Path]::IsPathRooted($versionFileFromManifest)) {
        $versionFilePath = $versionFileFromManifest
    } else {
        $versionFilePath = Join-Path $Root $versionFileFromManifest
    }
}

$buildPython = Resolve-BuildPython -RequestedPythonPath $PythonPath
Initialize-TclTkEnvironment -PythonExe $buildPython
Test-BuildPython -PythonExe $buildPython
Test-TkinterRuntime -PythonExe $buildPython

Write-WindowsVersionInfo `
    -Path $versionFilePath `
    -AppName $appName `
    -CompanyName $companyName `
    -Description $description `
    -VersionText $Version `
    -OriginalFilename $originalFilename
Write-Host "Version info actualizado: $versionFilePath"

if ([System.IO.Path]::IsPathRooted($ConfigPath)) {
    $resolvedConfigPath = $ConfigPath
} else {
    $resolvedConfigPath = Join-Path $Root $ConfigPath
}
if (-not (Test-Path $resolvedConfigPath)) {
    throw "No existe la configuracion de build: $resolvedConfigPath"
}

$config = Get-Content $resolvedConfigPath -Raw | ConvertFrom-Json
$argsList = [System.Collections.Generic.List[string]]::new()
$entrypoint = $null
$distPath = Join-Path $Root $DistDir
$workPath = Join-Path $Root "build\pyinstaller_work"
$specPath = Join-Path $Root "build\spec"
$hooksPath = Join-Path $Root "build_hooks"
$releasePath = Join-Path $distPath $ReleaseName

foreach ($option in $config.pyinstallerOptions) {
    $dest = [string]$option.optionDest
    $value = $option.value

    switch ($dest) {
        "noconfirm" { Add-FlagArg $argsList "--noconfirm" ([bool]$value) }
        "filenames" { $entrypoint = Resolve-ProjectPath ([string]$value) }
        "onefile" {
            if ([bool]$value) { $argsList.Add("--onefile") } else { $argsList.Add("--onedir") }
        }
        "console" {
            if ([bool]$value) { $argsList.Add("--console") } else { $argsList.Add("--windowed") }
        }
        "icon_file" { Add-ValueArg $argsList "--icon" (Resolve-ProjectPath ([string]$value)) }
        "name" { Add-ValueArg $argsList "--name" ([string]$value) }
        "upx_dir" { Add-ValueArg $argsList "--upx-dir" (Resolve-ProjectPath ([string]$value)) }
        "clean_build" { Add-FlagArg $argsList "--clean" ([bool]$value) }
        "optimize" { Add-ValueArg $argsList "--optimize" ([string]$value) }
        "strip" { Add-FlagArg $argsList "--strip" ([bool]$value) }
        "noupx" { Add-FlagArg $argsList "--noupx" ([bool]$value) }
        "hide_console" { Add-ValueArg $argsList "--hide-console" ([string]$value) }
        "disable_windowed_traceback" { Add-FlagArg $argsList "--disable-windowed-traceback" ([bool]$value) }
        "uac_admin" { Add-FlagArg $argsList "--uac-admin" ([bool]$value) }
        "uac_uiaccess" { Add-FlagArg $argsList "--uac-uiaccess" ([bool]$value) }
        "argv_emulation" { Add-FlagArg $argsList "--argv-emulation" ([bool]$value) }
        "bootloader_ignore_signals" { Add-FlagArg $argsList "--bootloader-ignore-signals" ([bool]$value) }
        "datas" { Add-ValueArg $argsList "--add-data" (Resolve-AddDataValue ([string]$value)) }
        "hiddenimports" { Add-ValueArg $argsList "--hidden-import" ([string]$value) }
        default { }
    }
}

$manualArgs = [string]$config.nonPyinstallerOptions.manualArguments
if (-not [string]::IsNullOrWhiteSpace($manualArgs)) {
    $manualTokens = [regex]::Matches($manualArgs, '"[^"]*"|\S+')
    foreach ($tokenMatch in $manualTokens) {
        $token = $tokenMatch.Value
        if ($token.StartsWith('"') -and $token.EndsWith('"')) {
            $token = $token.Substring(1, $token.Length - 2)
        }
        if (-not [string]::IsNullOrWhiteSpace($token)) {
            $argsList.Add($token)
        }
    }
}

Add-TclTkDataArgs -ArgsList $argsList
Add-VlcRuntimeArgs -ArgsList $argsList
Add-ValueArg $argsList "--additional-hooks-dir" $hooksPath
Add-ValueArg $argsList "--version-file" $versionFilePath
Add-ValueArg $argsList "--distpath" $distPath
Add-ValueArg $argsList "--workpath" $workPath
Add-ValueArg $argsList "--specpath" $specPath

if ([string]::IsNullOrWhiteSpace($entrypoint)) {
    throw "La configuracion no tiene optionDest=filenames."
}
$argsList.Add($entrypoint)

Write-Host "Compilando $ReleaseName v$Version..."
Write-Host "Config: $resolvedConfigPath"
Write-Host "Salida: $releasePath"

if ($DryRun) {
    Write-Host "DRY RUN - comando:"
    Write-Host "`"$buildPython`" -m PyInstaller $($argsList -join ' ')"
    exit 0
}

if (-not $NoClean) {
    if (Test-Path $releasePath) {
        Remove-Item -LiteralPath $releasePath -Recurse -Force
    }
    $zipPath = Join-Path $distPath "${ReleaseName}_v${Version}.zip"
    $hashPath = "$zipPath.sha256.txt"
    if (Test-Path $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    if (Test-Path $hashPath) { Remove-Item -LiteralPath $hashPath -Force }
}

& $buildPython -m PyInstaller @argsList
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller fallo con codigo $LASTEXITCODE usando Python: $buildPython"
}

if (-not (Test-Path $releasePath)) {
    throw "La compilacion finalizo, pero no se encontro la carpeta esperada: $releasePath"
}

if (-not $SkipPackage) {
    & (Join-Path $PSScriptRoot "package_release.ps1") `
        -Version $Version `
        -ReleaseName $ReleaseName `
        -SourceDir $releasePath `
        -OutputDir $distPath
}

Write-Host "Build finalizado correctamente."
