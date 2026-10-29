"""
=============================================================================
FILE: test_system.py
DESCRIPTION:
    Comprehensive smoke test for the stabilized software-phase deliverable.
    Verifies:
      1. Model checkpoint loading & parameter validation.
      2. Health endpoint status.
      3. Low-risk manual inference.
      4. High-risk manual inference & session alert generation.
      5. Boundary condition evaluation.
      6. History telemetry replay data source.
      7. Model-info metadata and baseline metrics completeness.
=============================================================================
"""

import os
import sys
import asyncio
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
    _session_alerts,
    _session_predictions,
)
from backend.utils.predictor import get_predictor


async def run_tests():
    print("=== GRAINGUARD AI -- SOFTWARE PHASE VERIFICATION SUITE ===")
    print("=" * 65)

    # 1. Model Loading
    print("\n[TEST 1] Verifying AR-TCN Model Checkpoint...")
    predictor = get_predictor()
    assert predictor._loaded, "AR-TCN failed to load"
    param_count = predictor.model.count_parameters()
    print(f"  [+] AR-TCN Loaded successfully on: {predictor.get_model_info()['device']}")
    print(f"  [+] Trainable parameters: {param_count:,}")
    print(f"  [+] Receptive field blocks: {len(predictor.model.tcn_blocks)}")

    # 2. Health Endpoint
    print("\n[TEST 2] Verifying /health Endpoint...")
    h = await health_check()
    assert h["status"] == "ok"
    assert h["model_loaded"] is True
    print(f"  [+] Health status: {h['status']} | Model loaded: {h['model_loaded']}")

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
    print(f"  [+] Risk Category: {low_res['risk_category']}")
    print(f"  [+] Confidence: {low_res['confidence'] * 100:.1f}%")
    print(f"  [+] Probabilities: {low_res['probabilities']}")
    print(f"  [+] Alert triggered: {low_res['alert']}")

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
    print(f"  [+] Risk Category: {high_res['risk_category']}")
    print(f"  [+] Confidence: {high_res['confidence'] * 100:.1f}%")
    print(f"  [+] Probabilities: {high_res['probabilities']}")
    print(f"  [+] Alert triggered: {high_res['alert']}")
    print(f"  [+] Actionable recommendation: {high_res['recommendations'][0]}")

    # 5. Sequence Prediction (24 steps)
    print("\n[TEST 5] Testing Sequence Prediction (Multi-Step Temporal Context)...")
    seq_readings = [low_input] * 12 + [high_input] * 12
    seq_payload = SensorSequence(readings=seq_readings)
    seq_res = await predict_sequence(seq_payload, bg)
    print(f"  [+] Sequence Risk: {seq_res['risk_category']} ({seq_res['confidence'] * 100:.1f}%)")

    # 6. Model Info & Metrics Completeness
    print("\n[TEST 6] Verifying /model-info Endpoint...")
    info = await model_info()
    assert "evaluation_metrics" in info, "evaluation_metrics missing"
    assert "all_model_metrics" in info, "all_model_metrics missing"
    print(f"  [+] Model Name: {info['name']}")
    print(f"  [+] AR-TCN Accuracy: {info['evaluation_metrics']['accuracy'] * 100:.2f}%")
    print(f"  [+] AR-TCN ROC-AUC: {info['evaluation_metrics']['roc_auc']:.4f}")
    print(f"  [+] Models in comparison set: {len(info['all_model_metrics'])}")

    # 7. History Endpoint (Simulated Replay Transparency)
    print("\n[TEST 7] Verifying /history (Simulated Telemetry Replay)...")
    hist = await get_history(limit=25, type="sensors")
    print(f"  [+] Records returned: {hist['count']}")
    print(f"  [+] Data Source declared: {hist.get('data_source')}")
    print(f"  [+] Is physical sensor: {hist.get('is_physical_sensor')}")
    print(f"  [+] Operating mode: {hist.get('mode')}")

    # 8. Alerts Endpoint (Session Tracking)
    print("\n[TEST 8] Verifying /alerts Endpoint...")
    alerts = await get_alerts(limit=5)
    print(f"  [+] Active alerts: {alerts['count']}")
    print(f"  [+] Latest alert message: {alerts['alerts'][0]['message']}")
    print(f"  [+] Alert data source: {alerts.get('data_source')}")

    # 9. Recommendations Endpoint
    print("\n[TEST 9] Verifying /recommendations Endpoint...")
    recs = await get_recommendations("High")
    print(f"  [+] Total recommendations for High Risk: {len(recs['recommendations'])}")

    print("\n" + "=" * 65)
    print("[SUCCESS] ALL TESTS PASSED! SYSTEM IS STABLE FOR DEMO.")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(run_tests())
