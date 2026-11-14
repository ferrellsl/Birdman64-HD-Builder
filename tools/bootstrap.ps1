# Fetches uv (a single-file Python runner, pinned and checksum-verified), which
# downloads its own Python 3.12 + Pillow + NumPy into tools\, then runs the
# builder. Nothing is installed system-wide.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root  = Split-Path -Parent $PSScriptRoot
$tools = Join-Path $root 'tools'
$uvDir = Join-Path $tools 'uv'
$uv    = Join-Path $uvDir 'uv.exe'

$UV_VERSION = '0.13.4'
$UV_SHA256  = 'CCEC7508A07D9933D7CB1261880633EFCF1F30D6E6EDDAB21823F1DAE6F23225'

if (-not (Test-Path $uv)) {
    Write-Host "Downloading uv $UV_VERSION (Python runner)..."
    New-Item -ItemType Directory -Force $uvDir | Out-Null
    $zip = Join-Path $uvDir 'uv.zip'
    Invoke-WebRequest "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-pc-windows-msvc.zip" -OutFile $zip
    $hash = (Get-FileHash $zip -Algorithm SHA256).Hash
    if ($hash -ne $UV_SHA256) { Remove-Item $zip; throw "uv download checksum mismatch ($hash)" }
    Expand-Archive $zip $uvDir -Force
    Remove-Item $zip
}

$env:UV_CACHE_DIR = Join-Path $tools 'uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $tools 'python'
$env:PYTHONUTF8 = '1'
Set-Location $root
& $uv run --quiet --no-project --python 3.12 --with 'pillow==13.0.0' --with 'numpy==2.4.2' -- python -m pw64hd.build @args
exit $LASTEXITCODE
