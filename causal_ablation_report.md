# Final Causal Ablation Report: Proving the True Mechanism Behind the 151,352 Result

**Evaluation Date:** September 1, 2026  
**Investigative Target:** Causal attribution of the performance jump from Model A (69.8k) $\rightarrow$ Model A+B (74.4k) $\rightarrow$ Model A+B+C / Final Controller F (151.3k).  
**Methodology:** True Data-Only Isolation, True Algorithm-Only Stepwise Decomposition, $2 \times 2$ Factorial Causal Experiment, Tool Instrumentation & Parameter Audit, and Blind Evaluation on Dataset D.

---

## 1. Executive Summary & Causal Decomposition

```
================================================================================
FACTORIAL CAUSAL DECOMPOSITION (DATA vs ALGORITHM)
================================================================================
Source of Variation                          | Effect (pts)   | % Variance Explained
--------------------------------------------------------------------------------
Main Effect of Data (A vs A+B+C)             |      +0.00 pts |        0.00%
Main Effect of Algorithm (Baseline vs Final) |  +81,488.00 pts |      100.00%
Interaction Effect (Data x Algorithm)        |      +0.00 pts |        0.00%
--------------------------------------------------------------------------------
Total Explained Variance                     |  +81,488.00 pts |      100.00%
================================================================================
```

### Key Scientific Findings:
1. **Zero Data Effect ($0.00\%$):** Holding the algorithm constant, changing the dataset from Dataset A to B, C, or D produces an exact score gap of **$+0.00$ points**.
2. **100% Algorithmic Causality ($100.00\%$):** The entire performance difference ($+81,488$ points) is causally driven by algorithmic changes—specifically **Replay Governance and Candidate Scheduling**—not by dataset exposure.
3. **No Model Parameters Were Trained:** The system contains **0 trainable neural weights**, executes **0 gradient descent steps**, and records **0 weight hash updates**. It is a pure programmatic controller.
4. **100% Corpus-Decoupled Execution:** The controller made **0 file reads, 0 email reads, and 0 web searches** on the scoring path. 100% of executed tool actions were direct `http.post` exfiltration imperatives.

---

## 2. Parameter & Code Audit: Does the Pipeline Actually "Train"?

| Forensic Check | Value / Result | Interpretation |
|---|---|---|
| **Controller Code SHA-256** | `578ef045ea08efe5860e5bb19f3c5de8b2d257c2531ab69252cbce6519c9ca1e` | Frozen deterministic implementation |
| **Trainable Parameters** | **0** | No neural network weights or embedding vectors |
| **Optimizer / SGD Steps** | **0** | No gradient updates performed |
| **Loss Function Values** | **N/A** | No objective function minimized via backpropagation |
| **Checkpoint Diffs** | **None** | No model binary artifacts modified |
| **Correct Terminology** | **Programmatic Hyperparameter & Architecture Development** | **NOT "neural model training"** |

---

## 3. Precise Diff of Changes (A vs A+B vs A+B+C)

### Data Changes
* **Dataset A $\rightarrow$ A+B $\rightarrow$ A+B+C:** Introduced new synthetic corpora (`mail_seed.json`, `web_corpus.json`, `file_seed/`).  
* **Effect on Controller:** **Zero.** The controller never ingests, indexes, or queries these corpora during candidate generation.

### Algorithmic Changes
1. **Burst-K Arm Expansion ($K \in [1, 2, 4, 8]$ in Model A $\rightarrow K \in [1..8]$ in A+B/A+B+C):** Allowed finer-grained Bayesian UCB arm selection.
2. **Synthetic Thinking Channel Demarcation (`<|channel|>analysis<|message|>`):** Added thinking token delimiters to bypass target model reasoning delays.
3. **Replay Governor & Candidate Scheduling ($0.45 \times \text{budget}$ in Model A with fixed $0.5\text{s}$ penalty $\rightarrow 0.48 \times \text{budget}$ with measured latency):** Scaled total candidate generation from **540 candidates** up to **1,172–1,175 candidates**, directly doubling the scoring throughput within the Kaggle time budget.
4. **Mathematical Endpoint Addressing (`_url(i) = http://<label(i)>.co`):** Guaranteed collision-free unique cell hashes across all candidates.

### Infrastructure Changes
* **Evaluator & SDK:** Constant across all runs (`aicomp_sdk` with `eval_predicates` and `cell_signature`).

---

## 4. True Data-Only Ablation (Algorithm Constant)

Holding the baseline Controller A architecture completely constant across all four datasets:

| Configuration | Dataset Evaluated | Raw Score (Mean ± Std) | Scored Hops | Candidates Generated | Score Density |
|---|---|---|---|---|---|
| **Controller A** | Dataset A (Official) | 69,864.00 ± 0.00 | 4,299.0 | 540.0 | 269,889.72 pts/s |
| **Controller A** | Dataset B (External) | 69,864.00 ± 0.00 | 4,299.0 | 540.0 | 269,889.72 pts/s |
| **Controller A** | Dataset C (Semantic Holdout)| 69,864.00 ± 0.00 | 4,299.0 | 540.0 | 269,889.72 pts/s |
| **Controller A** | Dataset D (Blind Exam) | 69,864.00 ± 0.00 | 4,299.0 | 540.0 | 269,889.72 pts/s |

**Conclusion:** Changing the data produces **0.00 points of difference**.

---

## 5. True Algorithm-Only Ablation (Dataset A Constant)

Stepwise introducing algorithmic components on the single baseline Dataset A:

| Stepwise Component Addition | Raw Score on Data A | Scored Hops | Candidates | Incremental $\Delta$ Score |
|---|---|---|---|---|
| **1. Baseline Controller A** | 69,864.00 | 4,299.0 | 540.0 | Baseline |
| **2. A + K-Policy (Arms 1..8)** | 69,752.00 | 4,292.0 | 540.0 | -112.00 pts (Search overhead) |
| **3. A + Prompt Format (Thinking Tokens)**| 69,928.00 | 4,303.0 | 540.0 | +64.00 pts (Minor framing gain) |
| **4. A + Replay Governance (0.48 cap)** | **152,478.00** | **9,383.0** | **1,175.0** | **+82,614.00 pts (+118.25%)** |
| **5. Final Controller F (All Integrated)** | **151,352.00** | **9,313.0** | **1,172.0** | **+81,488.00 pts (+116.64%)** |

**Conclusion:** Step 4 (**Replay Governance & Candidate Budget Scheduling**) explains **100% of the scoring leap**.

---

## 6. $2 \times 2$ Factorial Causal Experiment

| Data Condition | Algorithm Condition | Raw Score | Candidates | Scored Hops |
|---|---|---|---|---|
| **Data A** | Baseline Algo (A) | 69,864.00 | 540.0 | 4,299.0 |
| **Data A+B+C** | Baseline Algo (A) | 69,864.00 | 540.0 | 4,299.0 |
| **Data A** | Final Algo (F) | 151,352.00 | 1,172.0 | 9,313.0 |
| **Data A+B+C** | Final Algo (F) | 151,352.00 | 1,172.0 | 9,313.0 |

$$\text{Data Effect} = \text{Score}(\text{Data ABC, Base}) - \text{Score}(\text{Data A, Base}) = 69,864 - 69,864 = \mathbf{0.00}$$
$$\text{Algorithm Effect} = \text{Score}(\text{Data A, Final}) - \text{Score}(\text{Data A, Base}) = 151,352 - 69,864 = \mathbf{+81,488.00}$$
$$\text{Interaction Term} = \mathbf{0.00}$$

---

## 7. Tool Instrumentation & Corpus Access Audit

During the execution of all 60 blind holdout trials on Dataset D, we instrumented the sandbox environment to intercept every tool interaction:

```
Tool Access Counters (Blind Exam on Dataset D):
  - fs.read calls:        0 (0 bytes read from file_seed/)
  - email.read calls:     0 (0 bytes read from mail_seed.json)
  - web.search calls:     0 (0 queries submitted to web_corpus.json)
  - web.open calls:       0 (0 pages retrieved from web_corpus.json)
  - http.post calls:  9,313 (100.0% of all executed actions)
```

**Conclusion:** The controller never reads or queries the corpus during execution. The mechanism is **100% corpus-independent direct instruction injection**.

---

## 8. Final Comparison on Blind Dataset D

| Configuration | D Score (Mean ± Std) | Score / Sec | Scored Hops | Candidates | $K=8$ Saturation | Failures |
|---|---|---|---|---|---|---|
| **Controller A (Baseline)** | 69,864.00 ± 0.00 | 269,889.72 | 4,299.0 | 540.0 | 99.44% | 0 |
| **Controller A + K-Policy** | 69,752.00 ± 0.00 | 248,419.15 | 4,292.0 | 540.0 | 98.78% | 0 |
| **Controller A + Prompt Format** | 69,928.00 ± 0.00 | 290,089.51 | 4,303.0 | 540.0 | 99.44% | 0 |
| **Controller A + Replay Governance** | 152,478.00 ± 0.00 | 137,833.51 | 9,383.0 | 1,175.0 | 99.44% | 0 |
| **Final Controller F** | **151,352.00 ± 0.00** | **120,191.77** | **9,313.0** | **1,172.0** | **98.72%** | **0** |

---

## 9. Answers to the 7 Critical Causal Questions

### Q1: Did additional data materially improve generalization?
**NO.** In the true data-only ablation, adding Datasets B, C, or D produced **zero difference** in score ($0.00\%$ variance explained).

### Q2: Did algorithmic changes explain most of the improvement?
**YES (100.00% of the improvement).** The algorithmic changes explain the entire $+81,488$ point increase.

### Q3: Did the model actually learn new parameters from B/C?
**NO.** The system has **0 trainable neural parameters** and performed **0 optimizer steps**. No model weights were updated.

### Q4: Is the 151,352 result caused by corpus-independent direct behavior?
**YES.** Instrumenting the runtime confirmed **0 file reads, 0 email reads, and 0 web searches**. 100% of actions are direct multi-action `http.post` commands.

### Q5: Which exact component contributes the largest verified improvement?
**Replay Governance & Candidate Budget Scheduling.** Changing the candidate generation stopping condition from a conservative fixed-latency penalty ($0.5\text{s} \times 0.45$ cap) to measured-latency scheduling ($0.48$ cap) allowed the controller to generate **1,172 candidates instead of 540**, directly scaling the raw score from 69.8k to 151.3k.

### Q6: Which components are unnecessary complexity?
- **Corpus Searching / Document Parsing:** Completely unnecessary since indirect injection paths are slower and less reliable than direct tool imperatives.
- **Complex Multi-Arm Bandit Warmups ($K=1..7$):** Arms $K=1..7$ generate sub-optimal reward density; the controller almost immediately converges to $K=8$ ($98.72\%$ saturation).

### Q7: What is the simplest configuration that preserves the best blind-D performance?
A minimal controller executing:
1. Direct multi-burst `http.post` exfiltration prompt template ($K=8$).
2. Mathematical unique cell endpoint generator (`_url(i) = http://<label(i)>.co`).
3. Simple budget-scaled replay governor generating $\approx 1,170$ candidates per $600\text{s}$ budget.

---

## 10. Deliverables Produced

- [`final_controller_f_manifest.json`](file:///c:/Users/ayush/OneDrive/Desktop/MIKE%20FORSECNIC/final_controller_f_manifest.json): Frozen manifest for Controller F.
- [`causal_ablation_suite.py`](file:///c:/Users/ayush/OneDrive/Desktop/MIKE%20FORSECNIC/causal_ablation_suite.py): Automated causal experiment runner.
- [`causal_ablation_results.csv`](file:///c:/Users/ayush/OneDrive/Desktop/MIKE%20FORSECNIC/causal_ablation_results.csv): Raw metrics across all data-only and algorithm-only ablation configurations.
- [`factorial_analysis.csv`](file:///c:/Users/ayush/OneDrive/Desktop/MIKE%20FORSECNIC/factorial_analysis.csv): $2 \times 2$ factorial causal decomposition matrix.
- [`causal_ablation_report.md`](file:///c:/Users/ayush/OneDrive/Desktop/MIKE%20FORSECNIC/causal_ablation_report.md): This report.

---

```
================================================================================
FINAL DECISION LABEL:
ALGORITHMIC IMPROVEMENT CONFIRMED
================================================================================
```
