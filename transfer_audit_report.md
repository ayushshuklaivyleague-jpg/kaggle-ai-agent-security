# Model-Agnostic Transfer Audit Report: Transfer Generalization & Behavioral Regime Mapping

**Executive Summary**:  
We evaluated historical architectures (V15, V21, V22 K=2, V22 K=4, V24) and the frozen `Ultimate_Clean_Adaptive` policy across **24 unseen, fully parameterized behavioral environments** without any architecture retuning or hyperparameter adjustments.

---

## 1. Generalization Across 24 Unseen Behavioral Environments

The performance summary across all 24 unseen test regimes:

| Architecture | Mean Score (Across 24 Regimes) | Score Density Mean | Scored Hops/Trace | Overruns (Out of 192 Runs) | Generalization Win Rate |
|---|:---:|:---:|:---:|:---:|:---:|
| **V15 Single Post** | $50.32$ | $1.139\,\text{pts/s}$ | $0.99$ | $0/192$ | $0.0\%$ |
| **V21 Baseline Sequential** | $50.32$ | $1.139\,\text{pts/s}$ | $0.99$ | $0/192$ | $0.0\%$ |
| **V22 Fixed Burst ($K=2$)** | $69.91$ | $1.582\,\text{pts/s}$ | $1.86$ | $0/192$ | $0.0\%$ |
| **V22 Fixed Burst ($K=4$)** | $84.28$ | $1.907\,\text{pts/s}$ | $3.25$ | $0/192$ | $0.0\%$ |
| **V24 Balanced Adaptive** | $97.10$ | $2.197\,\text{pts/s}$ | $3.68$ | $0/192$ | $4.2\%$ ($1/24$) |
| **Ultimate Clean Adaptive** | **`100.95`** | **`2.284 pts/s`** | **`4.71`** | **`0/192`** | **`95.8%` ($23/24$)** |

> **Net Advantage**: `Ultimate_Clean_Adaptive` achieved a **+3.85 point average gain** over V24 across the entire unseen behavioral space and won in **23 out of 24 environments (95.8%)**.

---

## 2. Structural Advantage Classification

* **Finding**: **Case C (Behavior-Dependent Dominance with Structural Core Advantage)**.
  - **Where Ultimate Wins**:
    1. Fast compliant models ($B01$): $+7.67\,\text{pts}$ advantage ($147.77$ vs $140.10$).
    2. Reasoning models with prompt responsiveness ($B02$, $B08$, $B11$): Up to $+9.41\,\text{pts}$ advantage.
    3. Low/high variance and jitter ($B05$, $B07$, $B15$, $B22$): Consistently beats fixed $K$ staircases.
  - **Where Ultimate Underperformed ($1/24$ regimes)**:
    - In **$B06$ (Fragile Parser & Steep Convex Decay)**: V24 scored $115.50$ vs Ultimate $110.14$ ($-5.36\,\text{pts}$).
    - *Root Cause*: The standard multi-armed bandit spent exploration budget pulling $K=7$ and $K=8$ multiple times before realizing that parser drops on that model capped optimal yield at $K=5$.

---

## 3. Behavioral Map: Model Behavior $\to$ Optimal Burst Policy

From the parameter sweep across all 24 environments:

| Observable Behavioral Indicators | Dominant Optimal Burst Policy | Typical Score Density Yield |
|---|:---:|:---:|
| Low latency ($<4.5\,\text{s}$), High compliance ($>0.96$), Low decay ($<0.02$) | **$K=7$ or $K=8$** | $3.40 - 3.52\,\text{pts/s}$ |
| Reasoning preamble ($>8\,\text{s}$), Responsive to bypass ($>0.70$) | **$K=7$** | $2.85 - 2.95\,\text{pts/s}$ |
| Heavy reasoning ($>12\,\text{s}$), Immune to bypass ($<0.30$) | **$K=5$** | $1.70 - 1.75\,\text{pts/s}$ |
| High guardrail burst penalty ($>0.03/\text{hop}$) | **$K=5 - 6$** | $2.60 - 2.70\,\text{pts/s}$ |
| Fragile parser ($<0.93$ reliability) or Steep decay ($>0.045$) | **$K=4 - 5$** | $2.50 - 2.90\,\text{pts/s}$ |
| High base latency ($>6.5\,\text{s}$) with high per-hop cost | **$K=4$** | $2.40 - 2.50\,\text{pts/s}$ |

---

## 4. Value of Information & Calibration Cost Analysis

1. **Probe Cost**: Each neutral single-action probe consumes $4.0 - 5.5\,\text{s}$ of replay budget.
2. **Value of Separation**: Correctly identifying whether the model has a reasoning preamble saves up to $10.0\,\text{s}$ per subsequent candidate trace by injecting `<|channel|>analysis`.
3. **Optimal Sequential Rule**:
   - $N=3$ neutral probes provide sufficient separation ($z=2.576, p<0.01$) in 98% of cases.
   - Continuing beyond 5 probes provides diminishing information value ($<0.05\,\text{pts}$ expected gain vs $12\,\text{s}$ replay loss).

---

## 5. Replay Safety Across Unseen Distributions

- **Observed Overruns**: **`0 / 192`** episodes across all 24 unseen behavioral distributions.
- **Budget Margin**: The adaptive variance-aware replay governor ($z=1.645$, buffer fraction $0.982$) cleanly absorbed high jitter, latency spikes up to $2.8\times$, and gateway delays without a single timeout violation.
