# scripts/dev-start.ps1
# Starts PostgreSQL portable, Alembic migrations, FastAPI (uvicorn), and SvelteKit (vite dev)
# Usage: .\scripts\dev-start.ps1

$REPO_ROOT = Split-Path -Parent $PSScriptRoot
$PGDATA = "$REPO_ROOT\data\pgdata"
$PGBIN = "$REPO_ROOT\data\pgsql\bin"        # adjust to your Postgres portable bin location

# 1. Start Postgres if not already running
$pgRunning = & "$PGBIN\pg_ctl" status -D $PGDATA 2>$null | Select-String "server is running"
if (-not $pgRunning) {
    Write-Host "Starting PostgreSQL..."
    & "$PGBIN\pg_ctl" start -D $PGDATA -l "$PGDATA\logfile"
    Start-Sleep -Seconds 2
} else {
    Write-Host "PostgreSQL already running."
}

# 2. Run Alembic migrations
Push-Location $REPO_ROOT
Write-Host "Running Alembic migrations..."
alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Alembic migration failed. Check your DATABASE_URL in .env and ensure Postgres is running." -ForegroundColor Red
    Pop-Location
    exit 1
}

# 3. Start FastAPI in background
Write-Host "Starting FastAPI (uvicorn) on http://localhost:8000 ..."
$apiJob = Start-Job -ScriptBlock {
    Set-Location $using:REPO_ROOT
    uvicorn api.main:app --reload --port 8000
}

# 4. Start SvelteKit dev server in background
Write-Host "Starting SvelteKit dev server on http://localhost:5173 ..."
$appJob = Start-Job -ScriptBlock {
    Set-Location "$using:REPO_ROOT\app"
    npm run dev
}

Pop-Location
Write-Host ""
Write-Host "Services started." -ForegroundColor Green
Write-Host "  FastAPI:   http://localhost:8000" -ForegroundColor Cyan
Write-Host "  SvelteKit: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop all services."

# Keep running, show combined output from both jobs
try {
    while ($true) {
        Receive-Job $apiJob, $appJob
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Yellow
    Stop-Job $apiJob, $appJob
    Remove-Job $apiJob, $appJob
    Write-Host "Done." -ForegroundColor Green
}
