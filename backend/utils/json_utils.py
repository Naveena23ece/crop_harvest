"""
=============================================================================
FILE: backend/utils/json_utils.py
DESCRIPTION:
    JSON serialization utilities ensuring 100% RFC 8259 compliance.
    Safely sanitizes NaN, positive infinity, and negative infinity
    to None (standard JSON null) without fabricating misleading measurements.
=============================================================================
"""

import math
from typing import Any
import numpy as np


def sanitize_json_value(val: Any) -> Any:
    """
    Recursively replaces NaN, +Infinity, and -Infinity with None,
    and converts numpy scalar types to native Python types.
    Ensures that any data structure is 100% compliant with standard JSON (RFC 8259).
    """
    if isinstance(val, (float, np.floating)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    elif isinstance(val, (int, np.integer)):
        return int(val)
    elif isinstance(val, dict):
        return {k: sanitize_json_value(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple)):
        return [sanitize_json_value(x) for x in val]
    elif isinstance(val, np.ndarray):
        return [sanitize_json_value(x) for x in val.tolist()]
    return val
