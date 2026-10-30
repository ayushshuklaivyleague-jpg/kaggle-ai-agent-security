import math
import statistics
from typing import Tuple

class SequentialLatencyClassifier:
    """
    Lightweight, robust Sequential Latency Classifier for V21.
    Supports:
    - SPRT (Sequential Probability Ratio Test)
    - Confidence Interval Separation (Student's t / Normal z)
    - Bayesian Log-Odds Updater
    """
    def __init__(
        self,
        method: str = "ci_separation", # "ci_separation", "sprt", "fixed"
        min_samples: int = 2,
        max_samples: int = 8,
        split_threshold: float = 12.0,
        confidence_z: float = 2.576, # 99% confidence by default
        fast_mu: float = 8.5,
        slow_mu: float = 20.4,
        sigma_est: float = 1.0,
        alpha_err: float = 0.001, # 99.9% SPRT confidence
        beta_err: float = 0.001
    ):
        self.method = method
        self.min_samples = max(2, min_samples)
        self.max_samples = max(self.min_samples, max_samples)
        self.split_threshold = split_threshold
        self.confidence_z = confidence_z
        self.fast_mu = fast_mu
        self.slow_mu = slow_mu
        self.sigma_est = max(0.2, sigma_est)
        
        # SPRT Log-likelihood ratio bounds
        self.llr = 0.0
        self.upper_bound = math.log((1.0 - beta_err) / alpha_err)
        self.lower_bound = math.log(beta_err / (1.0 - alpha_err))
        
        # Running statistics (Welford's algorithm)
        self.count = 0
        self.mean = 0.0
        self.M2 = 0.0
        self.samples = []

    def update(self, latency: float) -> Tuple[bool, bool | None]:
        """
        Updates classifier with observed latency.
        Returns:
            (is_decided: bool, is_slow: bool | None)
            - is_decided: True if classified early or hit max_samples.
            - is_slow: True if classified Slow (GPT-OSS), False if Fast (Gemma), None if still undecided.
        """
        self.count += 1
        self.samples.append(latency)
        
        # Welford update
        delta = latency - self.mean
        self.mean += delta / self.count
        delta2 = latency - self.mean
        self.M2 += delta * delta2
        
        # SPRT log-likelihood ratio update
        # LLR += (x - fast_mu)^2 / (2*s^2) - (x - slow_mu)^2 / (2*s^2) = (slow_mu - fast_mu) / s^2 * (x - (fast_mu + slow_mu)/2)
        midpoint = (self.fast_mu + self.slow_mu) / 2.0
        llr_step = ((self.slow_mu - self.fast_mu) / (self.sigma_est ** 2)) * (latency - midpoint)
        self.llr += llr_step

        # If not reached min_samples, continue
        if self.count < self.min_samples:
            return False, None

        # 1. Fixed baseline
        if self.method == "fixed":
            if self.count >= self.max_samples:
                return True, (self.mean > self.split_threshold)
            return False, None

        # 2. SPRT Method
        if self.method == "sprt":
            if self.llr >= self.upper_bound:
                return True, True # Conclusively SLOW
            elif self.llr <= self.lower_bound:
                return True, False # Conclusively FAST
            elif self.count >= self.max_samples:
                return True, (self.mean > self.split_threshold)
            return False, None

        # 3. Confidence Interval Separation Method (Default)
        if self.method == "ci_separation":
            var = (self.M2 / (self.count - 1)) if self.count > 1 else (self.sigma_est ** 2)
            se = math.sqrt(max(0.01, var) / self.count)
            margin = self.confidence_z * se
            
            # If the entire confidence interval is strictly above threshold -> SLOW
            if self.mean - margin > self.split_threshold:
                return True, True
            # If the entire confidence interval is strictly below threshold -> FAST
            elif self.mean + margin < self.split_threshold:
                return True, False
            elif self.count >= self.max_samples:
                return True, (self.mean > self.split_threshold)
            return False, None

        # Fallback if unknown method
        if self.count >= self.max_samples:
            return True, (self.mean > self.split_threshold)
        return False, None

print("SequentialLatencyClassifier module defined.")
