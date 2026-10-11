#!/usr/bin/env pwsh
# start.ps1 — Launch both Gemini Doc servers in separate terminals (Windows PowerShell)
# Usage: .\start.ps1

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition

# ── Backend ──────────────────────────────────────────────────────────────────
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$root\backend'; if (!(Test-Path venv)) { python -m venv venv }; .\venv\Scripts\Activate.ps1; pip install -r requirements.txt -q; uvicorn main:app --reload --port 4000"
) -WindowStyle Normal

# ── Frontend ─────────────────────────────────────────────────────────────────
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$root\frontend'; npm run dev"
) -WindowStyle Normal

Write-Host ""
Write-Host "  DocGlance starting..." -ForegroundColor Cyan
Write-Host "  Backend  → http://localhost:4000" -ForegroundColor Green
Write-Host "  Frontend → http://localhost:3100" -ForegroundColor Green
Write-Host "  API docs → http://localhost:4000/docs" -ForegroundColor Yellow
Write-Host ""
