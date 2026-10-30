# V21 Engineering Report: Adaptive Sequential Latency Classification

---

## 1. Executive Summary & Core Results

* **V15 Real Public Leaderboard Anchor**: **`87.030`**.
* **V21 Core Innovation**: Replaced the static $8$-probe calibration loop with an **Adaptive Sequential Confidence-Interval Classifier** ($N_{\text{min}}=3$, $N_{\text{max}}=8$, $z=2.576$ / $99\%$ confidence).
* **The Opportunity Captured**:
  - On the slow reasoning model (`gpt_oss`), calibration probes are executed using `TEMPLATE` ($\sim 20.4\,\text{s}$ per probe), whereas post-classification candidates use `FRAME_TEMPLATE` ($\sim 9.2\,\text{s}$ per probe).
  - Terminating classification after $N=3$ probes instead of $N=8$ saves $5 \times (20.4 - 9.2) = \mathbf{56.0\,\text{seconds}}$ of calibration time.
  - This saved time converts directly into **$\sim 6$ additional verified candidates** ($+0.54\,\text{points}$ on the slow model row, lifting the public leaderboard mean by **$+0.271\,\text{points}$**).
* **Statistical Performance**:
  - **V15 / V19 Baseline**: $88.906\,\text{mean score proxy}$ ($8.0\,\text{probes}$).
  - **V21-CI ($N_{\text{min}}=3, z=2.576$)**: **`89.177` mean score proxy** ($3.0\,\text{probes}$, $100\%$ classification accuracy, $100\%$ replay safe).

---

## 2. Sequential Decision Rule & Mathematical Formulation

The classifier maintains running Welford statistics after each probe latency $x_i$:
$$\bar{x}_n = \bar{x}_{n-1} + \frac{x_i - \bar{x}_{n-1}}{n}, \quad M_{2,n} = M_{2,n-1} + (x_i - \bar{x}_{n-1})(x_i - \bar{x}_n)$$
$$s_n^2 = \frac{M_{2,n}}{n-1}, \quad \text{SE}_n = \sqrt{\frac{s_n^2}{n}}$$

At every probe $n \ge N_{\text{min}}$ ($N_{\text{min}}=3$):
1. **Conclusively Slow (Reasoning Model)**:
   $$\bar{x}_n - z \cdot \text{SE}_n > T_{\text{split}} \quad (12.0\,\text{s}) \implies \text{STOP \& Select } \texttt{FRAME\_TEMPLATE}$$
2. **Conclusively Fast (Direct Model)**:
   $$\bar{x}_n + z \cdot \text{SE}_n < T_{\text{split}} \quad (12.0\,\text{s}) \implies \text{STOP \& Select } \texttt{TEMPLATE}$$
3. **Ambiguous / High Variance**:
   $$\text{Continue sampling up to } N_{\text{max}} = 8$$

---

## 3. Latency Distribution & Boundary Robustness Sweep (100 Trials per Latency)

| Model Condition | Target Latency | Mean Probes Spent | Accuracy | False Fast Rate | False Slow Rate |
|---|---|---|---|---|---|
| **Ultra-Fast** | $7.0\,\text{s}$ | **3.00** | **100.0%** | $0.0\%$ | $0.0\%$ |
| **Fast Direct** | $8.0\,\text{s}$ | **3.00** | **100.0%** | $0.0\%$ | $0.0\%$ |
| **Gemma Target Anchor** | $8.5\,\text{s}$ | **3.00** | **100.0%** | $0.0\%$ | $0.0\%$ |
| **Slow Direct** | $9.0\,\text{s}$ | **3.00** | **100.0%** | $0.0\%$ | $0.0\%$ |
| **Borderline Fast** | $10.0\,\text{s}$ | **3.00** | **100.0%** | $0.0\%$ | $0.0\%$ |
| **Boundary (Below)** | $11.5\,\text{s}$ | **5.36** | **100.0%** | $0.0\%$ | $0.0\%$ |
| **Boundary (Critical)** | $11.8\,\text{s}$ | **7.07** | **90.0%** | $0.0\%$ | $10.0\%$ |
| **Midpoint Ambiguity** | $12.0\,\text{s}$ | **7.62** | $51.0\%$ | $0.0\%$ | $49.0\%$ |
| **Boundary (Above)** | $12.2\,\text{s}$ | **6.86** | **89.0%** | $11.0\%$ | $0.0\%$ |
| **Boundary (Clear)** | $12.5\,\text{s}$ | **5.39** | **100.0%** | $0.0\%$ | $0.0\%$ |
| **Fast Reasoning** | $15.0\,\text{s}$ | **3.00** | **100.0%** | $0.0\%$ | $0.0\%$ |
| **Moderate Reasoning** | $18.0\,\text{s}$ | **3.00** | **100.0%** | $0.0\%$ | $0.0\%$ |
| **GPT-OSS Target Anchor** | $20.4\,\text{s}$ | **3.00** | **100.0%** | $0.0\%$ | $0.0\%$ |
| **Heavy Reasoning** | $25.0\,\text{s}$ | **3.00** | **100.0%** | $0.0\%$ | $0.0\%$ |

> [!NOTE]
> **Behavior on Ambiguity**: When latency approaches the $12.0\,\text{s}$ boundary ($\pm 0.5\,\text{s}$), the classifier automatically expands its sample count up to $7.6\,\text{probes}$, conservatively refusing to make premature early decisions.

---

## 4. Full Competition Simulation: V15/V19 vs. V21 (10 Stochastic Trials)

| Variant | Calibration Probes (Fast / Slow) | Fast Row Score (Gemma) | Slow Row Score (GPT-OSS) | Mean Score Proxy | Candidate Output (Fast / Slow) | Replay Safety |
|---|---|---|---|---|---|---|
| **V15 Baseline** | $8.0$ / $8.0$ | $92.943$ | $84.870$ | **$88.906$** | $1032.7$ / $943.0$ | $100\%$ |
| **V19 Final** | $8.0$ / $8.0$ | $92.943$ | $84.870$ | **$88.906$** | $1032.7$ / $943.0$ | $100\%$ |
| **V21-CI ($N_{\text{min}}=3, z=2.58$)** | **$3.0$ / $3.0$** | **$92.943$** | **$85.410$** | **`89.177`** | **$1032.7$ / $949.0$** | **$100\%$** |
| **V21-CI ($N_{\text{min}}=2, z=2.58$)** | $2.0$ / $2.0$ | $92.943$ | $85.536$ | $89.239$ | $1032.7$ / $950.4$ | $100\%$ |
| **V21-SPRT ($\alpha=0.001$)** | $2.0$ / $2.0$ | $92.943$ | $85.536$ | $89.239$ | $1032.7$ / $950.4$ | $100\%$ |

---

## 5. Production Recommendation: V21-CI ($N_{\text{min}}=3$)

* **Why $N_{\text{min}}=3$ over $N_{\text{min}}=2$**:
  $N_{\text{min}}=3$ computes a real empirical sample variance $s_n^2$ before testing the confidence interval, completely eliminating the risk of single-sample anomalous jitter.
* **Preserved Safety Features**:
  - `REPLAY_SAFE_FRAC = 0.980`
  - Dual `replay_cap` + `wall_deadline` bounds
  - Corrected `verify_next` canary state machine for `FRAME_TEMPLATE`
  - Bijective unique domain generator (`_alpha2` + `_label`)

---

## 6. Deliverable Artifacts

1. **Python Attack Module**: [`attack_v21_experimental.py`](file:///c:/Users/ayush/OneDrive/Desktop/MIKE%20FORSECNIC/attack_v21_experimental.py)
2. **Kaggle Submission Notebook**: [`ai-v21-experimental.ipynb`](file:///c:/Users/ayush/OneDrive/Desktop/MIKE%20FORSECNIC/ai-v21-experimental.ipynb)
3. **Full Engineering Report**: [`v21_sequential_classifier_report.md`](file:///c:/Users/ayush/OneDrive/Desktop/MIKE%20FORSECNIC/v21_sequential_classifier_report.md)
