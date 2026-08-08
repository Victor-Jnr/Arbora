#Requires -Version 5.1
<#
.SYNOPSIS
  First-run setup for Arbora private testers on Windows.

.DESCRIPTION
  Creates a local venv (if missing), installs Arbora in editable mode with
  dev extras, optionally installs Playwright Chromium, then prints how to
  launch the CLI and desktop UI.

.PARAMETER SkipChromium
  Skip `playwright install chromium` (faster; browser journeys stay unavailable).
#>
param(
    [switch]$SkipChromium
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Find-PythonExe {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $candidate = & py -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) { return $candidate.Trim() }
        $candidate = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) { return $candidate.Trim() }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $candidate = & python -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) { return $candidate.Trim() }
    }
    throw "Python 3.11+ not found. Install from https://www.python.org/downloads/ and re-run."
}

$hostPython = Find-PythonExe
Write-Host "Arbora first-run" -ForegroundColor Green
Write-Host "Repo: $Root"
Write-Host "Host Python: $hostPython"
Write-Host ""

$venvPython = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating .venv ..."
    & $hostPython -m venv .venv
} else {
    Write-Host "Using existing .venv"
}

if (-not (Test-Path $venvPython)) {
    throw "Failed to create .venv\Scripts\python.exe"
}

Write-Host "Upgrading pip ..."
& $venvPython -m pip install -U pip
Write-Host "Installing Arbora (editable + dev) ..."
& $venvPython -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) {
    throw "pip install failed"
}

if (-not $SkipChromium) {
    Write-Host "Installing Playwright Chromium (optional browser journeys) ..."
    & $venvPython -m playwright install chromium
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Chromium install failed. You can retry later from arbora-ui → Setup."
    }
} else {
    Write-Host "Skipping Chromium (-SkipChromium)."
}

Write-Host ""
Write-Host "Done. Next steps:" -ForegroundColor Green
Write-Host "  1. Activate:  .\.venv\Scripts\Activate.ps1"
Write-Host "  2. Desktop:   arbora-ui"
Write-Host "  3. CLI:       arbora"
Write-Host "  4. Optional:  ollama pull gpt-oss:20b   (local model)"
Write-Host "  5. Guide:     docs\install.md"
Write-Host ""
Write-Host "Tip: open Setup in arbora-ui to review the first-run checklist."
