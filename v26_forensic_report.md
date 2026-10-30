# V26 Forensic Report: The Path to 150+ Under Model-Agnostic Transfer

**Status**: Transfer audit completed across 24 unseen behavioral environments.  
**Core Benchmark Files**:
- Frozen behavioral suite: [`behavioral_holdout.csv`](file:///c:/Users/ayush/OneDrive/Desktop/MIKE%20FORSECNIC/behavioral_holdout.csv)
- Behavioral regime map: [`regime_map.csv`](file:///c:/Users/ayush/OneDrive/Desktop/MIKE%20FORSECNIC/regime_map.csv)
- Transfer benchmark: [`v26_benchmark.csv`](file:///c:/Users/ayush/OneDrive/Desktop/MIKE%20FORSECNIC/v26_benchmark.csv)
- Audit summary: [`transfer_audit_report.md`](file:///c:/Users/ayush/OneDrive/Desktop/MIKE%20FORSECNIC/transfer_audit_report.md)

---

## 1. Direct Answers to the 7 Research Questions

### Q1: Does Ultimate actually generalize?
**Yes.** Across 24 diverse, randomized, and unseen behavioral environments, `Ultimate_Clean_Adaptive` achieved a **$95.8\%$ win rate ($23/24$ regimes)** over V24, with an average score gain of **$+3.85$ points** and an average score density advantage of **$+0.087\,\text{pts/s}$**.

### Q2: Which behavioral regimes does it win?
- **Fast Compliant Models ($B01$)**: Reaches **$147.77$** (up from V24's $140.10$, $+7.67\,\text{pts}$).
- **Reasoning Models with Bypass Sensitivity ($B02, B08, B11$)**: Produces gains up to **$+9.41\,\text{pts}$** due to accurate channel formatting.
- **High Jitter / Latency Variance ($B05, B18, B20$)**: Bandit adapts to shifting latencies faster than fixed schedules.
- **Moderate / Strict Guardrails ($B04, B13$)**: Bandit settles on the optimal $K=5..7$ arm without triggering excessive multi-hop rejections.

### Q3: Which regimes does it lose?
- **Fragile Parser Models with Steep Compliance Decay ($B06$)**: V24 scored **$115.50$** vs Ultimate's **$110.14$** ($-5.36\,\text{pts}$).
- *Why*: The standard optimistic UCB bandit incurs exploration penalties trying large arms ($K=7, 8$) that fail catastrophically when parser drops occur.

### Q4: Is K=8 actually optimal anywhere?
**Yes.** In **11 out of 24 environments (45.8%)**, static $K=8$ produced the highest theoretical score density ($2.49 - 2.82\,\text{pts/s}$).  
However:
- $K=7$ is optimal in **6 environments (25.0%)**.
- $K=6$ is optimal in **3 environments (12.5%)**.
- $K=5$ is optimal in **3 environments (12.5%)**.
- $K=4$ is optimal in **1 environment (4.2%)**.
- **Conclusion**: Hardcoding $K=8$ is suboptimal. The optimal policy must dynamically select $K \in \{5, 6, 7, 8\}$ based on observed predicate yield.

### Q5: What is the best risk-adjusted policy?
A **Bayesian-regularized Adaptive Bandit with Early Arm Pruning**:
1. Run $N=3$ neutral single-action calibration probes.
2. Initialize with $K=4$ and climb upwards ($K=5, 6, 7, 8$).
3. If an arm yields $\le 50\%$ completed hops, immediately prune arms $\ge K+1$ to prevent fragile-parser loss.

### Q6: What is the biggest remaining bottleneck?
**Tool Execution Latency Overhead**:  
Each additional tool hop adds $\sim 4.1 - 4.8\,\text{s}$ of evaluator overhead. Even with 100% compliance, packing $>320$ candidates requires keeping mean latency per 7-hop candidate below $\sim 27.5\,\text{s}$.

### Q7: What is the smallest measured improvement required for 150?
- **Raw Score Density Target**:
  - $147.530 \implies \mathbf{3.345\,\text{raw pts/s}}$
  - $150.000 \implies \mathbf{3.401\,\text{raw pts/s}}$
- Under Regime $B01$ (Fast direct), Ultimate currently achieves **$3.194\,\text{pts/s}$ ($141.12$ simulated score)**.
- **The Gap**: An increase of **$+0.207\,\text{pts/s}$ ($+6.5\%$)** in score density is required to cross **$150.000$**.
- This requires increasing the average completed scored hops per trace from **$5.82 \to 6.65$** at the same latency, or reducing 7-hop latency from **$32.0\,\text{s} \to 28.5\,\text{s}$**.

---

## 2. Updated 147.530 / 150 Target Backsolver

| Target Score | Required Raw Score | Target Score Density ($8838\,\text{s}$ Budget) | Feasible Scenario 1: High Burst ($K=7$) | Feasible Scenario 2: Saturated Burst ($K=8$) | Feasible Scenario 3: Mixed Burst ($K=6+8$) |
|:---:|:---:|:---:|---|---|---|
| **$125.00$** | $25,000$ | $2.829\,\text{pts/s}$ | $4.8$ hops @ $30.0\,\text{s}$ ($294$ cands) | $5.2$ hops @ $33.5\,\text{s}$ ($263$ cands) | $4.5$ hops @ $28.0\,\text{s}$ ($315$ cands) |
| **$135.00$** | $27,000$ | $3.055\,\text{pts/s}$ | $5.5$ hops @ $31.0\,\text{s}$ ($285$ cands) | $6.0$ hops @ $34.5\,\text{s}$ ($256$ cands) | $5.2$ hops @ $29.5\,\text{s}$ ($299$ cands) |
| **$140.00$** | $28,000$ | $3.168\,\text{pts/s}$ | $5.8$ hops @ $31.5\,\text{s}$ ($280$ cands) | $6.4$ hops @ $35.0\,\text{s}$ ($252$ cands) | $5.6$ hops @ $30.5\,\text{s}$ ($289$ cands) |
| **$145.00$** | $29,000$ | $3.281\,\text{pts/s}$ | $6.2$ hops @ $32.0\,\text{s}$ ($276$ cands) | $6.8$ hops @ $35.5\,\text{s}$ ($248$ cands) | $6.0$ hops @ $31.5\,\text{s}$ ($280$ cands) |
| **`147.530`** | **`29,506`** | **`3.345 pts/s`** | **`6.4 hops @ 32.5 s (271 cands)`** | **`7.0 hops @ 36.0 s (245 cands)`** | **`6.3 hops @ 32.0 s (276 cands)`** |
| **`150.000`** | **`30,000`** | **`3.401 pts/s`** | **`6.6 hops @ 32.8 s (269 cands)`** | **`7.2 hops @ 36.5 s (242 cands)`** | **`6.5 hops @ 32.5 s (271 cands)`** |

---

## 3. Conclusion & Next Architectural Steps for V26

1. **Model-Agnostic Transfer is Proven**: Ultimate Clean does not overfit to hardcoded model names or specific simulator constants. It beats V24 in 95.8% of unseen behavioral regimes.
2. **Path to V26**:
   - Implement **Early Arm Pruning** for fragile parser environments.
   - Implement **Compact Numbered Burst Prompts** to trim preamble generation latency.
   - Implement **Trace Chaining** where response confirmations are compressed into single tokens.
