#Requires -Version 5.1
<#
.SYNOPSIS
    Ubuntu Terra — one-command Windows dev launcher.

.DESCRIPTION
    Starts PostgreSQL (if installed locally), applies database migrations,
    seeds demo fields, starts the FastAPI backend, and starts the Vite frontend.

    Run from the repository root:
        .\scripts\dev.ps1

    Prerequisites (see /docs/LOCAL_SETUP_WINDOWS.md):
        - Python 3.10–3.13
        - Node.js 20+
        - PostgreSQL 15+ with PostGIS
        - DATABASE_URL set in .env at the repo root
#>

[CmdletBinding()]
param(
    [switch]$ResetDB,
    [switch]$NoSeed,
    [switch]$NoFrontend
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$databaseDir = Join-Path $repoRoot "database"
$venvPython = Join-Path $repoRoot "venv\Scripts\python.exe"

function Test-Command($cmd) {
    return [bool](Get-Command $cmd -ErrorAction SilentlyContinue)
}

function Ensure-Venv {
    if (-not (Test-Path $venvPython)) {
        Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
        python -m venv (Join-Path $repoRoot "venv")
    }
    & $venvPython -m pip install --upgrade pip | Out-Null
    & $venvPython -m pip install -r (Join-Path $backendDir "requirements.txt") | Out-Null
}

function Start-PostgreSQL {
    $pgService = Get-Service | Where-Object { $_.Name -like "*postgres*" -and $_.Status -ne "Running" } | Select-Object -First 1
    if ($pgService) {
        Write-Host "Starting PostgreSQL service $($pgService.Name)..." -ForegroundColor Cyan
        Start-Service -Name $pgService.Name
        Start-Sleep -Seconds 2
    }
}

function Invoke-Migrate {
    Write-Host "Applying database migrations..." -ForegroundColor Cyan
    $args = @("--seed")
    if ($ResetDB) { $args = @("--reset", "--seed") }
    elseif ($NoSeed) { $args = @() }
    & $venvPython (Join-Path $databaseDir "migrate.py") @args
}

function Start-Backend {
    Write-Host "Starting backend on http://localhost:8000 ..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendDir'; ..\..\venv\Scripts\python -m uvicorn app.main:app --reload --port 8000"
}

function Start-Frontend {
    if ($NoFrontend) { return }
    if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
        Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
        npm install --prefix $frontendDir
    }
    Write-Host "Starting frontend on http://localhost:5173 ..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; npm run dev"
}

# --- Main flow ---------------------------------------------------------------

Set-Location $repoRoot

if (-not (Test-Command "python")) {
    throw "Python is not installed or not on PATH. See /docs/LOCAL_SETUP_WINDOWS.md"
}
if (-not (Test-Command "npm")) {
    throw "npm is not installed or not on PATH. See /docs/LOCAL_SETUP_WINDOWS.md"
}
if (-not (Test-Command "psql")) {
    throw "psql is not installed or not on PATH. Ensure PostgreSQL bin directory is on PATH. See /docs/LOCAL_SETUP_WINDOWS.md"
}

Ensure-Venv
Start-PostgreSQL
Invoke-Migrate
Start-Backend
Start-Frontend

Write-Host "`nUbuntu Terra dev stack launching. Close the spawned PowerShell windows to stop services." -ForegroundColor Green
