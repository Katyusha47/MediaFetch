<#
build.ps1 - Build helper for MediaFetch (Windows PowerShell)

Usage:
  # Run once (installs pyinstaller if needed and builds)
  .\build.ps1 -InstallDeps

  # Run only the build step (assumes PyInstaller already installed)
  .\build.ps1

This script uses `python -m PyInstaller` (module invocation) to avoid "pyinstaller: command not found"
if `python` is not on PATH, replace `python` with full path to the Python executable.
#>

param(
    [switch]$InstallDeps,
    [switch]$OneDir,
    [switch]$IncludeFFmpeg,
    [string]$FFmpegPath = "",
    [switch]$Clean
)

# Make sure we're in the script folder
Set-Location -Path (Split-Path -Path $MyInvocation.MyCommand.Definition -Parent)

if ($InstallDeps) {
    Write-Host "Installing/Upgrading pip and PyInstaller..." -ForegroundColor Cyan
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    python -m pip install pyinstaller
}

# Build command
$exeName = "MediaFetch"
$icon = "icon.ico"

if ($Clean) {
    Write-Host "Cleaning build and dist folders..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue -Path .\build, .\dist, .\__pycache__
}

if ($OneDir) {
    $mode = "--onedir"
    Write-Host "Building in development mode (--onedir) for faster builds." -ForegroundColor Yellow
} else {
    $mode = "--onefile"
}

$addBinaryArg = ""
if ($IncludeFFmpeg) {
    # Determine ffmpeg path: use provided, else try common local paths
    if ([string]::IsNullOrEmpty($FFmpegPath)) {
        $cand1 = Join-Path -Path (Get-Location) -ChildPath "ffmpeg.exe"
        $cand2 = Join-Path -Path (Get-Location) -ChildPath "ffmpeg\bin\ffmpeg.exe"
        $cand3 = Join-Path -Path (Get-Location) -ChildPath "bin\ffmpeg.exe"
        if (Test-Path $cand1) { $FFmpegPath = $cand1 }
        elseif (Test-Path $cand2) { $FFmpegPath = $cand2 }
        elseif (Test-Path $cand3) { $FFmpegPath = $cand3 }
    }

    if (-not [string]::IsNullOrEmpty($FFmpegPath) -and (Test-Path $FFmpegPath)) {
        # PyInstaller expects a <SRC;DEST> pair, use '.' as dest to put next to exe
        $addBinaryArg = "--add-binary `"$FFmpegPath;.`" 
        Write-Host "Including FFmpeg from: $FFmpegPath" -ForegroundColor Green
    } else {
        Write-Host "Warning: FFmpeg include requested but ffmpeg.exe not found. Skipping include." -ForegroundColor Yellow
    }
}

$specArgs = "$mode --windowed --name `"$exeName`" --icon=$icon $addBinaryArg main.py"

Write-Host "Running PyInstaller (module invocation) with args: $specArgs" -ForegroundColor Cyan
if (-not [string]::IsNullOrEmpty($addBinaryArg)) {
    python -m PyInstaller $mode --windowed --name "$exeName" --icon=$icon $addBinaryArg main.py
} else {
    python -m PyInstaller $mode --windowed --name "$exeName" --icon=$icon main.py
}

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build completed. EXE is in the 'dist' folder." -ForegroundColor Green
} else {
    Write-Host "PyInstaller failed. See the output above for details." -ForegroundColor Red
}
