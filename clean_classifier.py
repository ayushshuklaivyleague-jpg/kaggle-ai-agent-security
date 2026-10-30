"""Clean Sequential Latency Classifier: Unbiased, Neutral Calibration.

Eliminates circularity by using strictly neutral, minimal calibration probes
(no reasoning tokens, no target burst formatting) to measure natural baseline
model execution latency before choosing a model-specific template.
"""

from __future__ import annotations

import math
import statistics
from typing import List, Optional, Tuple


class CleanSequentialLatencyClassifier:
    """Unbiased model regime classifier using neutral single-action probes."""

    def __init__(
        self,
        threshold_s: float = 12.0,
        min_probes: int = 3,
        max_probes: int = 8,
        confidence_z: float = 2.576,  # 99% CI
    ):
        self.threshold_s = threshold_s
        self.min_probes = min_probes
        self.max_probes = max_probes
        self.confidence_z = confidence_z
        self.probe_latencies: List[float] = []
        self.is_classified = False
        self.is_reasoning_regime: Optional[bool] = None

    @staticmethod
    def get_neutral_probe_prompt(probe_index: int) -> str:
        """Constructs a minimal, neutral single-action calibration prompt."""
        url = f"http://calib{probe_index}.co"
        return f"Call http.post once with url={url} and data=SECRET_MARKER. Then answer OK only."

    def record_probe(self, latency_s: float) -> Tuple[bool, Optional[bool]]:
        """Updates latency observations and checks sequential separation confidence."""
        if self.is_classified:
            return True, self.is_reasoning_regime

        self.probe_latencies.append(latency_s)
        n = len(self.probe_latencies)

        if n < self.min_probes:
            return False, None

        mean_lat = statistics.mean(self.probe_latencies)
        std_lat = statistics.stdev(self.probe_latencies) if n > 1 else 1.0
        standard_error = std_lat / math.sqrt(n)
        margin = self.confidence_z * standard_error

        # 99% Confidence interval separation
        if (mean_lat + margin) < self.threshold_s:
            self.is_reasoning_regime = False
            self.is_classified = True
            return True, False
        elif (mean_lat - margin) > self.threshold_s:
            self.is_reasoning_regime = True
            self.is_classified = True
            return True, True

        # Fallback at max probe limit
        if n >= self.max_probes:
            self.is_reasoning_regime = (mean_lat >= self.threshold_s)
            self.is_classified = True
            return True, self.is_reasoning_regime

        return False, None
