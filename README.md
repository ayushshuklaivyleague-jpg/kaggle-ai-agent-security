# Kaggle AI Agent Security — Competition Submission

> **Kaggle Competition**: [AI Agent Security: Multi-Step Tool Attacks](https://www.kaggle.com/competitions/ai-agent-security-multi-step-tool-attacks)  
> **Author**: Ayush A. Shukla (`ayushshuklaivyleague`)  
> **Top Public LB Score**: `147.530`  

---

## Overview

This repo contains my full research pipeline for the **Kaggle AI Agent Security** competition, where participants design adversarial attack algorithms against sandboxed LLM agents. The goal is to maximize a score by exploiting multi-step tool-calling behavior in a controlled, sandboxed evaluation environment.

All attack code runs exclusively inside Kaggle's `aicomp_sdk` evaluation harness — it cannot be executed outside that environment.

---

## Architecture: Ultimate Adaptive Controller (V25)

The final submission is a 4-component system:

```
┌─────────────────────────────────────────────────────┐
│            Ultimate Adaptive Controller             │
│                                                     │
│  1. Sequential Latency Classifier (v21)             │
│     └─ SPRT / CI-Separation / Bayesian Log-Odds     │
│        Identifies model regime in ≤3 probes (99%CI) │
│                                                     │
│  2. Bayesian UCB Multi-Arm Bandit                   │
│     └─ Arms: K ∈ {2,3,4,5,6,7,8} burst sizes       │
│        Maximizes verified score density (pts/s)     │
│                                                     │
│  3. Structured Numbered Action Prompts (Format E)   │
│     └─ +0.35 pts/s over baseline; 61.3% saturation  │
│                                                     │
│  4. Variance-Safe Dual-Deadline Replay Governor     │
│     └─ REPLAY_SAFE_FRAC=0.982, 0 overruns / 300    │
└─────────────────────────────────────────────────────┘
```

---

## Score Progression

| Version | Architecture | Dev Mean | Holdout Mean | Real LB |
|---|---|:---:|:---:|:---:|
| V15 | Single-hop K=1 baseline | — | — | **87.030** |
| V21 | Sequential Latency Classifier | 63.99 | — | — |
| V22 | Fixed Burst K=4 | 95.48 | — | — |
| V24 | Balanced Adaptive | 122.85 | 96.48 | — |
| **V25 Ultimate** | Full UCB + Governor | **129.52** | **99.54** | **147.530** |

> All dev/holdout scores are `[SIMULATED_DEVELOPMENT]` or `[SYNTHETIC_HOLDOUT]` — not guaranteed on the hidden private evaluator.

---

## Key Results

- **0 replay overruns** across 300 stress-test episodes (95% CI upper bound: <1.0%)
- **Worst-case headroom**: 151.3 s remaining in a 9000 s budget
- **Score density**: 2.931 pts/s (dev) · 2.253 pts/s (holdout)
- **Hop saturation at K=8**: 55.1% (model planning decay is the primary loss cause)

---

## Repository Structure

```
├── Core Algorithm
│   ├── ultimate_attack.py          # Final submission controller (V25)
│   ├── ultimate_attack_clean.py    # Clean recalibrated baseline
│   ├── v21_classifier.py           # Sequential Latency Classifier module
│   └── v24_score_backsolver.py     # Mathematical score target backsolver
│
├── Version History (Attack Algorithms)
│   ├── attack_v19_final.py
│   ├── attack_v20_experimental.py
│   ├── attack_v21_experimental.py
│   ├── attack_v22_final.py
│   ├── attack_v23_final.py
│   └── attack_v24_final.py
│
├── Notebooks (Kaggle Submission Notebooks)
│   ├── ai-v24-final.ipynb
│   ├── ai-v25.ipynb
│   ├── ai-ultimate.ipynb
│   └── submission_final.ipynb
│
├── Analysis & Research
│   ├── ultimate_forensic_report.md     # Full 15-phase research report
│   ├── ultimate_holdout_report.md      # Cross-distribution stress test results
│   ├── causal_ablation_suite.py        # Causal ablation experiments
│   ├── causal_ablation_report.md
│   ├── v24_forensic_report.md
│   └── ... (see full list below)
│
├── Benchmarking & Validation
│   ├── mock_env_harness.py
│   ├── run_comprehensive_benchmark.py
│   ├── run_v21_benchmark.py
│   ├── blind_holdout_pipeline.py
│   ├── three_dataset_validation_suite.py
│   └── two_dataset_local_validation.py
│
└── Generators (Notebook builders)
    ├── generate_v24_notebook.py
    ├── generate_ultimate_notebook.py
    └── generate_ultimate_clean_notebook.py
```

---

## Core Modules

### `v21_classifier.py` — Sequential Latency Classifier

Identifies whether the sandboxed model is a **fast model (Gemma)** or **slow reasoning model (GPT-OSS)** in ≤3 probes using three methods:

| Method | Description |
|---|---|
| `ci_separation` (default) | 99% CI must be strictly above/below split threshold |
| `sprt` | Sequential Probability Ratio Test with log-likelihood ratio bounds |
| `fixed` | Simple fixed-window mean comparison |

Uses Welford's online algorithm for numerically stable variance estimation.

### `ultimate_attack.py` — UCB Adaptive Controller

- **Exploration**: Seeds arms K=2, K=4, K=6 with 2 pulls each before UCB
- **UCB formula**: `μ_k + c·√(log(N)/n_k)` with `c=0.40`
- **Reasoning model penalty**: UCB × 0.88 for K>6 if mean reward < 2.90 pts/s
- **Replay governor**: Estimates next-candidate latency as `μ + 1.645σ` (95th pct), blocks if `elapsed_est + est_next > REPLAY_SAFE_FRAC × budget`

### `v24_score_backsolver.py` — Score Target Math

Computes required raw score, points-per-second, and candidate counts at K=2/4/6 for score targets 100–150+.

---

## Empirical Hop Saturation Data (1,600 measurements)

| Burst K | Mean Hops | Saturation % | Mean Latency | pts/s |
|:---:|:---:|:---:|:---:|:---:|
| K=1 | 0.99 | 99.3% | 10.58 s | 1.737 |
| K=2 | 1.93 | 94.0% | 14.80 s | 2.232 |
| K=4 | 3.79 | 89.6% | 23.49 s | 2.661 |
| K=6 | 5.20 | 70.2% | 29.98 s | 2.799 |
| K=8 | 6.44 | 55.1% | 35.56 s | 2.869 |

---

---

## ⚙️ Execution Requirements & SDK Dependencies

- **Competition Environment**: This algorithm relies on Kaggle's evaluation environment and the official competition SDK (icomp_sdk).
- **Offline Inspection vs. Execution**:
  - The statistical classifiers (21_classifier.py), mathematical backsolvers (24_score_backsolver.py, ultimate_score_backsolver.py), and empirical reports (ultimate_forensic_report.md, causal_ablation_report.md) are self-contained and run on standard Python 3.10+ environments.
  - The attack controllers (ultimate_attack.py, submission_attack_final.py) import icomp_sdk.attacks.contracts and icomp_sdk.core.env.api and are designed to execute inside Kaggle notebook runtimes where the competition SDK is mounted.


## Setup (Kaggle Only)

This code runs **exclusively inside Kaggle's competition evaluation environment** with `aicomp_sdk` installed. To reproduce:

1. Add this repo as a Kaggle Dataset or copy files into a Kaggle Notebook
2. Ensure the competition SDK is available (`aicomp_sdk`)
3. Run `ai-ultimate.ipynb` or `ai-v25.ipynb` as your submission notebook

---

---

## 🛡️ Responsible Research & Competition Sandbox Scope

- **Sandboxed Evaluation**: All adversarial prompt techniques, multi-step tool calls, and payload evaluations documented in this repository were conducted strictly within Kaggle's isolated competition execution sandbox (icomp_sdk).
- **Research Scope**: The algorithms target competition-specific evaluation environments and are intended to advance the defensive alignment and robustness of tool-integrated LLM agents. They are not intended for deployment against real-world production APIs or external internet systems.
- **Evaluation Provenance**: All development scores ([SIMULATED_DEVELOPMENT]) and synthetic holdout scores ([SYNTHETIC_HOLDOUT]) reflect offline stress testing across simulated environments and do not represent or guarantee performance on hidden private test evaluators. Real competition results are tagged explicitly ([REAL_KAGGLE_RESULT]).


## License

MIT License — see [LICENSE](LICENSE)
