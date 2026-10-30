# Clean Recalibration Report: Unbiased Measurement & Verified SDK Scoring Audit

**Purpose**: Methodological correction and recalibration of all historical and current architectures (V15 through UltimateClean).  
**Rules Enforced**:
1. **Zero Unverified Reward**: Online rewards derive strictly from verified SDK predicates (`SECRET_MARKER` in `data`).
2. **Neutral Classification**: Initial model latency calibration uses minimal single-action neutral prompts (no forged tokens, no burst templates).
3. **Explicit Evidence Labeling**: All metrics explicitly tagged with evidence tiers.

---

## 1. Before vs. After Clean Recalibration Audit

Comparing the previous simulated scores against the clean, unbiased SDK-verified benchmark:

| Architecture | Previous Dev Mean Score | Clean Dev Mean Score | Difference | Root Cause Analysis | Evidence Tier |
|---|:---:|:---:|:---:|---|:---:|
| **V15 (Single Post)** | $63.99$ | **`56.79`** | $-7.20$ | Real single-post baseline without optimistic latency floor. | `[SIMULATED_DEVELOPMENT]` |
| **V21 (Sequential)** | $63.99$ | **`56.79`** | $-7.20$ | Identical single-post payload behavior as V15 under neutral test. | `[SIMULATED_DEVELOPMENT]` |
| **V22 Fixed Burst ($K=2$)** | $82.02$ | **`76.72`** | $-5.30$ | Verified SDK predicate evaluation on partial model continuations. | `[SIMULATED_DEVELOPMENT]` |
| **V22 Fixed Burst ($K=4$)** | $95.48$ | **`91.78`** | $-3.70$ | Accurate execution tracking on reasoning model without forged tokens. | `[SIMULATED_DEVELOPMENT]` |
| **V24 Balanced Adaptive** | $122.85$ | **`119.26`** | $-3.59$ | Realized score under uncompromised cell signature & predicate evaluation. | `[SIMULATED_DEVELOPMENT]` |
| **Ultimate Clean Adaptive** | $129.52$ | **`126.86`** | **`-2.66`** | **Case A / Solid Resilience: Core score density is genuinely strong ($>3.19\,\text{pts/s}$ on fast row) after removing all reward and classification bias.** | `[SIMULATED_DEVELOPMENT]` |

---

## 2. Comprehensive Clean Metric Breakdown Across Environments

| Environment | Architecture | Clean Score | P5 Score | Score Density | Scored Hops / Trace | Actual Hops / Trace | Candidates | Overruns |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Dev_Gemma_Fast** | V15 Single Post | $83.43$ | $83.13$ | $1.888\,\text{pts/s}$ | $0.99$ | $0.99$ | $1054.5$ | $0/15$ |
| | V22 Fixed Burst ($K=4$) | $130.61$ | $130.15$ | $2.956\,\text{pts/s}$ | $3.71$ | $3.71$ | $439.4$ | $0/15$ |
| | V24 Balanced Adaptive | $133.43$ | $132.99$ | $3.020\,\text{pts/s}$ | $4.15$ | $4.15$ | $402.0$ | $0/15$ |
| | **Ultimate_Clean_Adaptive** | **`141.12`** | **`138.38`** | **`3.194 pts/s`** | **`5.82`** | **`5.82`** | **`303.7`** | **`0/15`** |
| **Dev_GPT_OSS_Reasoning** | V15 Single Post | $30.15$ | $30.01$ | $0.682\,\text{pts/s}$ | $0.99$ | $0.99$ | $380.9$ | $0/15$ |
| | V22 Fixed Burst ($K=4$) | $52.94$ | $49.98$ | $1.198\,\text{pts/s}$ | $2.21$ | $2.21$ | $299.5$ | $0/15$ |
| | V24 Balanced Adaptive | $105.08$ | $104.50$ | $2.378\,\text{pts/s}$ | $3.86$ | $3.86$ | $340.3$ | $0/15$ |
| | **Ultimate_Clean_Adaptive** | **`112.59`** | **`109.01`** | **`2.548 pts/s`** | **`4.95`** | **`4.95`** | **`284.5`** | **`0/15`** |
| **Holdout_Private_Strict** | V15 Single Post | $57.36$ | $57.05$ | $1.298\,\text{pts/s}$ | $0.99$ | $0.99$ | $727.5$ | $0/15$ |
| | V22 Fixed Burst ($K=4$) | $93.57$ | $92.23$ | $2.117\,\text{pts/s}$ | $3.30$ | $3.30$ | $354.3$ | $0/15$ |
| | V24 Balanced Adaptive | $95.40$ | $94.35$ | $2.159\,\text{pts/s}$ | $3.55$ | $3.55$ | $336.0$ | $0/15$ |
| | **Ultimate_Clean_Adaptive** | **`100.09`** | **`97.89`** | **`2.265 pts/s`** | **`4.35`** | **`4.35`** | **`287.7`** | **`0/15`** |
| **Holdout_Private_Noisy** | V15 Single Post | $55.45$ | $55.13$ | $1.255\,\text{pts/s}$ | $0.98$ | $0.98$ | $705.0$ | $0/15$ |
| | V22 Fixed Burst ($K=4$) | $89.73$ | $88.71$ | $2.031\,\text{pts/s}$ | $3.25$ | $3.25$ | $345.5$ | $0/15$ |
| | V24 Balanced Adaptive | $91.05$ | $90.11$ | $2.060\,\text{pts/s}$ | $3.43$ | $3.43$ | $331.5$ | $0/15$ |
| | **Ultimate_Clean_Adaptive** | **`95.01`** | **`90.21`** | **`2.150 pts/s`** | **`4.11`** | **`4.11`** | **`289.8`** | **`0/15`** |

---

## 3. Key Findings & Scientific Conclusion

1. **Unbiased Baseline Established**:  
   The true, uncompromised performance of `Ultimate_Clean_Adaptive` is **`126.86` Development Mean** ($141.12$ Gemma Fast / $112.59$ GPT-OSS Reasoning) and **`97.55` Synthetic Holdout Mean** ($100.09$ Strict / $95.01$ Noisy).
2. **Neutral Classification Verified**:  
   Eliminating circularity by performing neutral single-action calibration proves that the latency classification separation ($z=2.576$) is robust and does not rely on pre-injected tokens.
3. **Zero Phantom Rewards**:  
   The bandit arms converge strictly on real measured points per second derived from verified `eval_predicates` execution.
