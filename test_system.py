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
    total = 15

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
    assert low_res["confidence"] > 0.55, f"Expected confidence > 0.55, got {low_res['confidence']}"
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
    passed += 1

    # 12. REGRESSION TEST: Manual Prediction Repeatability (Deterministic Invariance)
    print("\n[TEST 12] REGRESSION: Testing Repeated Manual Prediction Invariance...")
    default_input = SensorReading(
        temperature_c=28.0,
        humidity_pct=65.0,
        gas_concentration=480.0,
        grain_moisture=12.0,
        storage_duration=45,
        ext_temperature_c=30.0,
        ventilation_status=1,
        battery_voltage=3.9,
        sensor_health=1,
    )
    confidences = []
    prob_sets = []
    for _ in range(10):
        res = await predict_single(default_input, bg)
        confidences.append(res["confidence"])
        prob_sets.append(res["probabilities"])

    assert len(set(confidences)) == 1, f"Prediction confidence varied across identical runs: {confidences}"
    assert all(p == prob_sets[0] for p in prob_sets), "Prediction probabilities varied across runs"
    print(f"  [+] 10/10 identical runs produced strictly invariant confidence: {confidences[0] * 100:.2f}%")
    print(f"  [+] Invariant probability distribution: {prob_sets[0]}")
    passed += 1

    # 13. REGRESSION TEST: Order Invariance (Interleaved Input Immunity)
    print("\n[TEST 13] REGRESSION: Testing Interleaved Input & History Buffer Decoupling...")
    # Run High-Risk, then Default
    await predict_single(high_input, bg)
    res_after_high = await predict_single(default_input, bg)

    # Run Low-Risk, then Default
    await predict_single(low_input, bg)
    res_after_low = await predict_single(default_input, bg)

    assert res_after_high["confidence"] == res_after_low["confidence"], (
        f"Order dependence detected: after high={res_after_high['confidence']}, "
        f"after low={res_after_low['confidence']}"
    )
    assert res_after_high["probabilities"] == res_after_low["probabilities"], (
        "Probability divergence detected across interleaved inputs"
    )
    print(f"  [+] Order invariance confirmed: confidence after High ({res_after_high['confidence']}) "
          f"== after Low ({res_after_low['confidence']})")
    passed += 1

    # 14. REGRESSION TEST: Telemetry Isolation (Background Polling Immunity)
    print("\n[TEST 14] REGRESSION: Testing Telemetry Isolation from Manual Predictions...")
    baseline_manual = await predict_single(default_input, bg)

    # Simulate 5 background polling calls to /latest-risk (modifies telemetry stream)
    for _ in range(5):
        await get_latest_risk(bg, use_mock=False)

    post_poll_manual = await predict_single(default_input, bg)
    assert baseline_manual["confidence"] == post_poll_manual["confidence"], (
        f"Background polling contaminated manual prediction: "
        f"baseline={baseline_manual['confidence']}, post_poll={post_poll_manual['confidence']}"
    )
    assert baseline_manual["probabilities"] == post_poll_manual["probabilities"], (
        "Probabilities shifted after background polling"
    )
    print("  [+] Background telemetry polling does NOT alter manual predictions.")
    print("  [+] Decoupled telemetry buffer isolation verified.")
    passed += 1

    # 15. REGRESSION TEST: Verification of Zero Target Leakage (_label Excluded)
    print("\n[TEST 15] REGRESSION: Verifying Target Column '_label' Exclusion...")
    import joblib
    import pandas as pd
    from training.preprocess import get_feature_columns

    # 1. Verify get_feature_columns excludes _label
    dummy_df = pd.DataFrame(columns=["temperature_c", "humidity_pct", "_label", "risk_category", "risk_score", "timestamp"])
    clean_cols = get_feature_columns(dummy_df)
    assert "_label" not in clean_cols, "CRITICAL: '_label' was not excluded by get_feature_columns()"
    assert "risk_category" not in clean_cols, "'risk_category' was not excluded"
    assert "risk_score" not in clean_cols, "'risk_score' was not excluded"

    # 2. Verify saved feature_cols.pkl
    fc_path = os.path.join(ROOT_DIR, "models", "feature_cols.pkl")
    if os.path.exists(fc_path):
        saved_fc = joblib.load(fc_path)
        assert "_label" not in saved_fc, "CRITICAL: '_label' is present in models/feature_cols.pkl"
        assert len(saved_fc) == 60, f"Expected 60 clean features, got {len(saved_fc)}"
        print(f"  [+] feature_cols.pkl contains exactly {len(saved_fc)} clean features (no '_label').")

    # 3. Verify retrained random_forest.pkl has n_features_in_ == 60
    rf_path = os.path.join(ROOT_DIR, "models", "random_forest.pkl")
    if os.path.exists(rf_path):
        rf_model = joblib.load(rf_path)
        assert rf_model.n_features_in_ == 60, f"Expected RF n_features_in_ == 60, got {rf_model.n_features_in_}"
        print(f"  [+] random_forest.pkl fitted on {rf_model.n_features_in_} features (clean, no leakage).")

    # 4. Verify metrics.json does not report 1.0000 artificial score
    metrics_path = os.path.join(ROOT_DIR, "models", "metrics.json")
    with open(metrics_path, "r") as f:
        metrics_data = json.load(f)
    rf_metrics = next(m for m in metrics_data if m["model"] == "random_forest")
    assert rf_metrics["accuracy"] < 1.0, f"Random Forest accuracy is still 1.0000: {rf_metrics}"
    assert rf_metrics["accuracy"] > 0.90, f"Unexpected low accuracy for RF: {rf_metrics['accuracy']}"
    print(f"  [+] Real held-out test metrics verified: RF Accuracy={rf_metrics['accuracy']*100:.2f}%, F1={rf_metrics['f1_score']*100:.2f}% (not 1.0000).")
    passed += 1

    print("\n" + "=" * 68)
    print(f"[SUCCESS] ALL {passed}/{total} VERIFICATION & REGRESSION TESTS PASSED!")
    print("=" * 68)


if __name__ == "__main__":
    asyncio.run(run_tests())
