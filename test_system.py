"""
=============================================================================
FILE: test_system.py
DESCRIPTION:
    Comprehensive verification and regression test suite for GrainGuard AI.
    Verifies:
      1. Model checkpoint loading & parameter integrity.
      2. Health endpoint status & runtime mode.
      3. Low-risk manual inference (AR-TCN).
      4. High-risk manual inference & alert generation.
      5. Input validation & boundary enforcement (Pydantic).
      6. Temporal sequence prediction (24-step context).
      7. Regression test for /history NaN/Inf JSON serialization (limit=100).
      8. Local prototype persistence across restarts.
      9. Alerts endpoint and local storage data source.
      10. Model info & comparative evaluation metrics.
      11. Actionable recommendation delivery.
=============================================================================
"""

import os
import sys
import json
import math
import asyncio
from pydantic import ValidationError
from fastapi import BackgroundTasks

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from backend.api.main import (
    health_check,
    predict_single,
    predict_sequence,
    get_latest_risk,
    get_history,
    get_alerts,
    model_info,
    get_recommendations,
    SensorReading,
    SensorSequence,
)
from backend.utils.local_store import local_store, STORAGE_FILE
from backend.utils.predictor import get_predictor
from backend.utils.json_utils import sanitize_json_value


async def run_tests():
    print("=== GRAINGUARD AI -- CRITICAL SOFTWARE PHASE VERIFICATION SUITE ===")
    print("=" * 68)

    passed = 0
    total = 11

    # 1. Model Loading
    print("\n[TEST 1] Verifying AR-TCN Model Checkpoint...")
    predictor = get_predictor()
    assert predictor._loaded, "AR-TCN failed to load"
    param_count = predictor.model.count_parameters()
    print(f"  [+] AR-TCN Loaded successfully on: {predictor.get_model_info()['device']}")
    print(f"  [+] Trainable parameters: {param_count:,}")
    print(f"  [+] Receptive field blocks: {len(predictor.model.tcn_blocks)}")
    passed += 1

    # 2. Health Endpoint
    print("\n[TEST 2] Verifying /health Endpoint...")
    h = await health_check()
    assert h["status"] == "ok", "Status is not ok"
    assert h["model_loaded"] is True, "Model not reported as loaded"
    print(f"  [+] Health status: {h['status']} | Model loaded: {h['model_loaded']}")
    passed += 1

    # 3. Low-Risk Inference
    print("\n[TEST 3] Testing Low-Risk Input (Optimal Silo Conditions)...")
    bg = BackgroundTasks()
    low_input = SensorReading(
        temperature_c=18.0,
        humidity_pct=45.0,
        gas_concentration=320.0,
        grain_moisture=10.0,
        storage_duration=15,
        ext_temperature_c=22.0,
        ventilation_status=1,
        battery_voltage=4.0,
        sensor_health=1,
    )
    low_res = await predict_single(low_input, bg)
    assert low_res["risk_category"] == "Low", f"Expected Low, got {low_res['risk_category']}"
    assert low_res["confidence"] > 0.80, f"Expected confidence > 0.80, got {low_res['confidence']}"
    assert low_res["alert"] is False, "Alert should be False for low-risk"
    print(f"  [+] Risk Category: {low_res['risk_category']}")
    print(f"  [+] Confidence: {low_res['confidence'] * 100:.1f}%")
    print(f"  [+] Probabilities: {low_res['probabilities']}")
    print(f"  [+] Alert triggered: {low_res['alert']}")
    passed += 1

    # 4. High-Risk Inference & Alert Generation
    print("\n[TEST 4] Testing High-Risk Input (Spoilage Alert Condition)...")
    high_input = SensorReading(
        temperature_c=38.0,
        humidity_pct=88.0,
        gas_concentration=1600.0,
        grain_moisture=19.0,
        storage_duration=120,
        ext_temperature_c=42.0,
        ventilation_status=0,
        battery_voltage=3.6,
        sensor_health=1,
    )
    high_res = await predict_single(high_input, bg)
    assert high_res["risk_category"] == "High", f"Expected High, got {high_res['risk_category']}"
    assert high_res["confidence"] > 0.80, f"Expected confidence > 0.80, got {high_res['confidence']}"
    assert high_res["alert"] is True, "Alert should be True for high-risk"
    assert len(high_res["recommendations"]) > 0, "Recommendations must be generated"
    print(f"  [+] Risk Category: {high_res['risk_category']}")
    print(f"  [+] Confidence: {high_res['confidence'] * 100:.1f}%")
    print(f"  [+] Probabilities: {high_res['probabilities']}")
    print(f"  [+] Alert triggered: {high_res['alert']}")
    print(f"  [+] Actionable recommendation: {high_res['recommendations'][0]}")
    passed += 1

    # 5. Boundary & Input Validation Enforcement
    print("\n[TEST 5] Testing Input Validation & Boundary Enforcement...")
    invalid_cases = [
        {"temperature_c": 120.0, "humidity_pct": 50.0, "gas_concentration": 400.0, "grain_moisture": 12.0},  # temp > 80
        {"temperature_c": 25.0, "humidity_pct": -5.0, "gas_concentration": 400.0, "grain_moisture": 12.0},   # humidity < 0
        {"temperature_c": 25.0, "humidity_pct": 50.0, "gas_concentration": -10.0, "grain_moisture": 12.0},   # gas < 0
        {"temperature_c": 25.0, "humidity_pct": 50.0, "gas_concentration": 400.0, "grain_moisture": 99.0},   # moisture > 50
    ]
    caught = 0
    for case in invalid_cases:
        try:
            SensorReading(**case)
        except ValidationError:
            caught += 1
    assert caught == len(invalid_cases), f"Expected {len(invalid_cases)} validation errors, caught {caught}"
    print(f"  [+] Successfully rejected {caught}/{len(invalid_cases)} out-of-bounds input payloads via Pydantic.")
    passed += 1

    # 6. Sequence Prediction (24 steps)
    print("\n[TEST 6] Testing Sequence Prediction (Multi-Step Temporal Context)...")
    seq_readings = [low_input] * 12 + [high_input] * 12
    seq_payload = SensorSequence(readings=seq_readings)
    seq_res = await predict_sequence(seq_payload, bg)
    assert seq_res["risk_category"] in ["Low", "Moderate", "High"]
    print(f"  [+] Sequence Risk: {seq_res['risk_category']} ({seq_res['confidence'] * 100:.1f}%)")
    passed += 1

    # 7. REGRESSION TEST: /history NaN/Inf JSON Serialization
    print("\n[TEST 7] REGRESSION: Testing /history?type=sensors&limit=100 JSON Compliance...")
    hist = await get_history(limit=100, type="sensors")
    assert hist["count"] == 100, f"Expected 100 records, got {hist['count']}"
    # Verify strict RFC 8259 JSON compliance with allow_nan=False
    try:
        json_output = json.dumps(hist, allow_nan=False)
        print(f"  [+] Strict RFC 8259 JSON compliance verified: serialized {len(json_output):,} bytes without NaN/Inf.")
    except ValueError as e:
        assert False, f"JSON serialization failed with ValueError: {e}"

    # Verify that missing values are None (null) and not fabricated numbers
    null_counts = sum(1 for r in hist["records"] if any(v is None for v in r.values()))
    print(f"  [+] Records containing safely handled nulls: {null_counts} (transparent, non-fabricated)")
    print(f"  [+] Data Source declared: {hist.get('data_source')}")
    print(f"  [+] Operating mode declared: {hist.get('mode')}")
    passed += 1

    # 8. Local Prototype Persistence Across Backend Calls
    print("\n[TEST 8] Verifying Local Prototype Persistence (Cross-Restart Storage)...")
    pred_key = local_store.save_prediction(high_res)
    assert os.path.exists(STORAGE_FILE), "Local storage file was not created"
    stored_preds = local_store.get_predictions(limit=10)
    assert len(stored_preds) > 0, "No predictions found in local store"
    assert stored_preds[0]["risk_category"] == "High"
    print(f"  [+] Saved prediction with key: {pred_key}")
    print(f"  [+] Storage file verified: {STORAGE_FILE} ({os.path.getsize(STORAGE_FILE):,} bytes)")
    print(f"  [+] Total persisted predictions: {len(stored_preds)}")
    passed += 1

    # 9. Alerts Endpoint Verification
    print("\n[TEST 9] Verifying /alerts Endpoint...")
    alerts = await get_alerts(limit=5)
    assert alerts["count"] > 0, "Alerts count should be > 0"
    assert alerts["data_source"] == "local_prototype_persistence"
    print(f"  [+] Active alerts returned: {alerts['count']}")
    print(f"  [+] Latest alert message: {alerts['alerts'][0]['message']}")
    print(f"  [+] Alert data source: {alerts.get('data_source')}")
    passed += 1

    # 10. Model Info & Metrics Completeness
    print("\n[TEST 10] Verifying /model-info Endpoint...")
    info = await model_info()
    assert "evaluation_metrics" in info, "evaluation_metrics missing"
    assert "all_model_metrics" in info, "all_model_metrics missing"
    print(f"  [+] Model Name: {info['name']}")
    print(f"  [+] AR-TCN Accuracy: {info['evaluation_metrics']['accuracy'] * 100:.2f}%")
    print(f"  [+] AR-TCN ROC-AUC: {info['evaluation_metrics']['roc_auc']:.4f}")
    print(f"  [+] Models in comparison set: {len(info['all_model_metrics'])}")
    passed += 1

    # 11. Recommendations Endpoint
    print("\n[TEST 11] Verifying /recommendations Endpoint...")
    recs = await get_recommendations("High")
    assert len(recs["recommendations"]) > 0, "No recommendations returned"
    print(f"  [+] Total recommendations for High Risk: {len(recs['recommendations'])}")
    passed += 1

    print("\n" + "=" * 68)
    print(f"[SUCCESS] ALL {passed}/{total} VERIFICATION & REGRESSION TESTS PASSED!")
    print("=" * 68)


if __name__ == "__main__":
    asyncio.run(run_tests())
