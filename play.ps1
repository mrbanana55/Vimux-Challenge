$ErrorActionPreference = "Stop"

$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $RepoDir ".venv"

if (Test-Path (Join-Path $VenvDir "Scripts\python.exe")) {
    $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
} else {
    $VenvPython = Join-Path $VenvDir "bin\python"
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating virtual environment in .venv..."
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $VenvDir
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $VenvDir
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        & python3 -m venv $VenvDir
    } else {
        Write-Error "Python (>= 3.11) is required to run Vimux Challenge."
        exit 1
    }

    if (Test-Path (Join-Path $VenvDir "Scripts\python.exe")) {
        $VenvPython = Join-Path $VenvDir "Scripts\python.exe"
    } else {
        $VenvPython = Join-Path $VenvDir "bin\python"
    }
}

$null = & $VenvPython -c "import textual" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing dependencies into .venv..."
    & $VenvPython -m pip install --quiet -r (Join-Path $RepoDir "requirements.txt")
}

$SrcDir = Join-Path $RepoDir "src"
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$SrcDir$([System.IO.Path]::PathSeparator)$($env:PYTHONPATH)"
} else {
    $env:PYTHONPATH = $SrcDir
}

& $VenvPython -m vim_tmux_quest @args
exit $LASTEXITCODE
