# ============================================================
# FILE: deployment/run_pipeline.ps1
# One-click Windows PowerShell script to run the full pipeline:
#   1. Install Python dependencies
#   2. Generate dataset
#   3. Run preprocessing
#   4. Train all models
#   5. Evaluate all models
#   6. Start the FastAPI backend
# ============================================================

param(
    [switch]$SkipDataGen   = $false,
    [switch]$SkipTraining  = $false,
    [switch]$SkipEval      = $false,
    [string]$Model         = "artcn"
)

$ErrorActionPreference = "Stop"
$ROOT = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ROOT
Write-Host "=== GrainGuard AI Pipeline ===" -ForegroundColor Green
Write-Host "Root: $ROOT"

# ── Step 1: Install dependencies ─────────────────────────
Write-Host "`n[STEP 1] Installing Python dependencies ..." -ForegroundColor Cyan
pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed"; exit 1 }
Write-Host "Dependencies installed." -ForegroundColor Green

# ── Step 2: Generate dataset ─────────────────────────────
if (-not $SkipDataGen) {
    Write-Host "`n[STEP 2] Generating synthetic dataset ..." -ForegroundColor Cyan
    python dataset/generate_dataset.py
    if ($LASTEXITCODE -ne 0) { Write-Error "Dataset generation failed"; exit 1 }
    Write-Host "Dataset generated." -ForegroundColor Green
} else {
    Write-Host "`n[STEP 2] Skipping dataset generation." -ForegroundColor Yellow
}

# ── Step 3 + 4: Train models ──────────────────────────────
if (-not $SkipTraining) {
    Write-Host "`n[STEP 3+4] Running preprocessing + training (model=$Model) ..." -ForegroundColor Cyan
    python training/train.py --model $Model
    if ($LASTEXITCODE -ne 0) { Write-Error "Training failed"; exit 1 }
    Write-Host "Training complete." -ForegroundColor Green
} else {
    Write-Host "`n[STEP 3+4] Skipping training." -ForegroundColor Yellow
}

# ── Step 5: Evaluate ──────────────────────────────────────
if (-not $SkipEval) {
    Write-Host "`n[STEP 5] Running evaluation ..." -ForegroundColor Cyan
    python training/evaluate.py
    if ($LASTEXITCODE -ne 0) { Write-Warning "Evaluation had errors (non-fatal)" }
    Write-Host "Evaluation complete." -ForegroundColor Green
} else {
    Write-Host "`n[STEP 5] Skipping evaluation." -ForegroundColor Yellow
}

# ── Step 6: Start backend ─────────────────────────────────
Write-Host "`n[STEP 6] Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop the server." -ForegroundColor Gray
Write-Host "  Swagger UI: http://localhost:8000/docs" -ForegroundColor Gray
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
