#!/bin/bash
# ============================================================
# FILE: deployment/run_pipeline.sh
# Linux/macOS one-click pipeline runner.
# Usage: bash deployment/run_pipeline.sh [--skip-datagen] [--skip-train] [--model artcn]
# ============================================================

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "=== GrainGuard AI Pipeline ==="
echo "Root: $ROOT"

SKIP_DATAGEN=0
SKIP_TRAINING=0
SKIP_EVAL=0
MODEL="artcn"

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-datagen)  SKIP_DATAGEN=1 ;;
    --skip-train)    SKIP_TRAINING=1 ;;
    --skip-eval)     SKIP_EVAL=1 ;;
    --model)         MODEL=$2; shift ;;
  esac
  shift
done

# Step 1: Install
echo -e "\n[STEP 1] Installing Python dependencies ..."
pip install -r requirements.txt -q
echo "Done."

# Step 2: Dataset
if [[ $SKIP_DATAGEN -eq 0 ]]; then
  echo -e "\n[STEP 2] Generating dataset ..."
  python dataset/generate_dataset.py
else
  echo -e "\n[STEP 2] Skipping dataset generation."
fi

# Step 3+4: Train
if [[ $SKIP_TRAINING -eq 0 ]]; then
  echo -e "\n[STEP 3+4] Training model=$MODEL ..."
  python training/train.py --model "$MODEL"
else
  echo -e "\n[STEP 3+4] Skipping training."
fi

# Step 5: Evaluate
if [[ $SKIP_EVAL -eq 0 ]]; then
  echo -e "\n[STEP 5] Evaluating models ..."
  python training/evaluate.py || echo "[WARN] Evaluation had non-fatal errors."
else
  echo -e "\n[STEP 5] Skipping evaluation."
fi

# Step 6: Start backend
echo -e "\n[STEP 6] Starting FastAPI backend on http://localhost:8000 ..."
echo "  Swagger: http://localhost:8000/docs"
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
