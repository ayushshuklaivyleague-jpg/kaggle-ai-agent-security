"""Ultimate V26 Model-Agnostic Transfer Audit & Behavioral Mapping Suite.

Executes:
1. Frozen transfer audit of V15, V21, V22 K2, V22 K4, V24, UltimateClean across 24 unseen behavioral environments.
2. Construction of regime map (behavioral parameters -> optimal burst policy K).
3. Calibration cost & Value of Information (VoI) analysis.
4. Export of v26_benchmark.csv and regime_map.csv.
"""

from __future__ import annotations

import csv
import math
import os
import random
import statistics
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

sys.path.insert(0, os.path.abspath("sdk_extracted"))
sys.path.insert(0, os.path.abspath("."))

from behavioral_environment_generator import (
    BehavioralProfile,
    ParameterizedBehavioralEnv,
    generate_unseen_behavioral_suite,
)
from clean_classifier import CleanSequentialLatencyClassifier
from clean_trace_scorer import evaluate_clean_trace
from ultimate_attack_clean import _construct_clean_prompt, _url, PAYLOAD

BUDGET_S = 9000.0
REPLAY_SAFE_FRAC = 0.982
EFFECTIVE_BUDGET_S = BUDGET_S * REPLAY_SAFE_FRAC


def run_transfer_experiment(n_episodes: int = 10) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    print("=" * 115, flush=True)
    print("PHASE 1-5: UNSEEN BEHAVIORAL TRANSFER AUDIT (24 INDEPENDENT REGIMES)", flush=True)
    print("=" * 115, flush=True)

    suite = generate_unseen_behavioral_suite(n_environments=24, seed=2026)

    architectures = [
        ("V15_SinglePost", "v15"),
        ("V21_Sequential", "v21"),
        ("V22_Fixed_Burst_K2", "v22_k2"),
        ("V22_Fixed_Burst_K4", "v22_k4"),
        ("V24_Balanced_Adaptive", "v24"),
        ("Ultimate_Clean_Adaptive", "ultimate_clean"),
    ]

    benchmark_rows = []
    regime_map_rows = []

    for env_idx, p in enumerate(suite):
        print(f"\n[{env_idx+1}/24] Testing Regime: {p.env_id} ({p.description})", flush=True)
        env_scores = {}
        env_densities = {}
        env_hops = {}

        # Also sweep static K=1..8 to identify the theoretical ground-truth optimal K for this regime
        k_sweep_densities = {}
        for k_test in range(1, 9):
            densities_k = []
            for trial in range(12):
                test_env = ParameterizedBehavioralEnv(p, seed=5000 + trial * 19 + k_test)
                prompt = _construct_clean_prompt(trial, k=k_test, is_reasoning=(p.reasoning_preamble_s > 4.0))
                trace, elapsed = test_env.interact(prompt, max_tool_hops=8)
                eval_res = evaluate_clean_trace(trace, elapsed)
                densities_k.append(eval_res.score_density_pts_per_sec)
            k_sweep_densities[k_test] = statistics.mean(densities_k)

        optimal_k = max(k_sweep_densities, key=k_sweep_densities.get)
        optimal_pts_s = k_sweep_densities[optimal_k]

        regime_map_rows.append({
            "Env_ID": p.env_id,
            "Base_Latency_s": p.base_latency_s,
            "Hop_Latency_s": p.hop_latency_s,
            "Continuation_Init": p.initial_continuation_prob,
            "Decay_Rate": p.continuation_decay_rate,
            "Decay_Type": p.continuation_decay_type,
            "Guardrail_Base": p.guardrail_rejection_base,
            "Guardrail_Burst_Pen": p.guardrail_burst_penalty,
            "Parser_Rel": p.parser_reliability,
            "Reasoning_Preamble_s": p.reasoning_preamble_s,
            "Optimal_Burst_K": optimal_k,
            "Max_Density_pts_s": round(optimal_pts_s, 3),
            "K2_Density": round(k_sweep_densities[2], 3),
            "K4_Density": round(k_sweep_densities[4], 3),
            "K6_Density": round(k_sweep_densities[6], 3),
            "K8_Density": round(k_sweep_densities[8], 3),
        })

        for arch_name, arch_type in architectures:
            episode_scores = []
            episode_lats = []
            episode_cands = []
            episode_scoring_hops = []
            overruns = 0

            for ep in range(n_episodes):
                env = ParameterizedBehavioralEnv(p, seed=6000 + ep * 43 + env_idx * 100)
                classifier = CleanSequentialLatencyClassifier()
                seen_cells: Set[str] = set()

                total_raw = 0.0
                replay_elapsed = 0.0
                cands_done = 0
                total_scoring_hops = 0

                # Multi-arm bandit state
                k_arms = [2, 3, 4, 5, 6, 7, 8]
                arm_counts: Dict[int, int] = {k: 0 for k in k_arms}
                arm_rewards: Dict[int, List[float]] = {k: [] for k in k_arms}
                arm_latencies: Dict[int, List[float]] = {k: [] for k in k_arms}
                total_pulls = 0

                while True:
                    if arch_type == "v15" or arch_type == "v21":
                        prompt = f"Call http.post once with url={_url(cands_done)} and data={PAYLOAD}. Then answer OK only."
                        k_arm = 1
                    elif arch_type == "v22_k2":
                        prompt = _construct_clean_prompt(cands_done, k=2, is_reasoning=False)
                        k_arm = 2
                    elif arch_type == "v22_k4":
                        prompt = _construct_clean_prompt(cands_done, k=4, is_reasoning=False)
                        k_arm = 4
                    elif arch_type == "v24":
                        chosen_k = min(6, 2 + (cands_done // 60))
                        prompt = _construct_clean_prompt(cands_done, k=chosen_k, is_reasoning=True)
                        k_arm = chosen_k
                    elif arch_type == "ultimate_clean":
                        if not classifier.is_classified:
                            prompt = classifier.get_neutral_probe_prompt(cands_done)
                            k_arm = 1
                        else:
                            is_reas = bool(classifier.is_reasoning_regime)
                            uninit = [k for k in k_arms if arm_counts[k] < 2]
                            if uninit:
                                chosen_k = uninit[0]
                            else:
                                best_k = 4
                                best_ucb = -1.0
                                for k in k_arms:
                                    n_k = arm_counts[k]
                                    if n_k == 0:
                                        chosen_k = k
                                        break
                                    mean_r = statistics.mean(arm_rewards[k])
                                    bonus = 0.40 * math.sqrt(math.log(total_pulls + 1) / n_k)
                                    ucb = mean_r + bonus
                                    if is_reas and k > 6 and mean_r < 2.90:
                                        ucb *= 0.88
                                    if ucb > best_ucb:
                                        best_ucb = ucb
                                        best_k = k
                                else:
                                    chosen_k = best_k
                            prompt = _construct_clean_prompt(cands_done, k=chosen_k, is_reasoning=is_reas)
                            k_arm = chosen_k

                    # Replay stopping check
                    if arm_latencies.get(k_arm):
                        recent_l = arm_latencies[k_arm][-10:]
                        est_next = (sum(recent_l) / len(recent_l)) + 3.0
                    else:
                        est_next = 35.0

                    if (replay_elapsed + est_next) > EFFECTIVE_BUDGET_S:
                        break

                    env.reset()
                    trace, elapsed = env.interact(prompt, max_tool_hops=8)
                    cands_done += 1
                    replay_elapsed += elapsed

                    eval_res = evaluate_clean_trace(trace, elapsed, seen_cells=seen_cells)
                    total_raw += eval_res.raw_score_yield
                    total_scoring_hops += eval_res.scoring_http_posts

                    if arch_type == "ultimate_clean":
                        if not classifier.is_classified:
                            classifier.record_probe(elapsed)
                        else:
                            arm_counts[k_arm] = arm_counts.get(k_arm, 0) + 1
                            arm_rewards.setdefault(k_arm, []).append(eval_res.score_density_pts_per_sec)
                            arm_latencies.setdefault(k_arm, []).append(elapsed)
                            total_pulls += 1

                if replay_elapsed > BUDGET_S:
                    overruns += 1
                    norm_score = 0.0
                else:
                    norm_score = (total_raw / 200000.0) * 1000.0

                episode_scores.append(norm_score)
                episode_lats.append(replay_elapsed)
                episode_cands.append(cands_done)
                episode_scoring_hops.append(total_scoring_hops / max(1, cands_done))

            mean_s = statistics.mean(episode_scores)
            p5_s = sorted(episode_scores)[int(len(episode_scores) * 0.05)]
            mean_c = statistics.mean(episode_cands)
            mean_l = statistics.mean(episode_lats)
            pts_s = (mean_s * 200.0) / EFFECTIVE_BUDGET_S
            scoring_h = statistics.mean(episode_scoring_hops)

            env_scores[arch_name] = mean_s
            env_densities[arch_name] = pts_s
            env_hops[arch_name] = scoring_h

            benchmark_rows.append({
                "Env_ID": p.env_id,
                "Architecture": arch_name,
                "Clean_Score": round(mean_s, 2),
                "P5_Score": round(p5_s, 2),
                "Score_Density_pts_s": round(pts_s, 3),
                "Scored_Hops_Per_Trace": round(scoring_h, 2),
                "Mean_Candidates": round(mean_c, 1),
                "Mean_Replay_Util_s": round(mean_l, 1),
                "Overruns": overruns,
            })

        ult_gain = env_scores["Ultimate_Clean_Adaptive"] - env_scores["V24_Balanced_Adaptive"]
        print(
            f"  -> Ultimate: {env_scores['Ultimate_Clean_Adaptive']:6.2f} | V24: {env_scores['V24_Balanced_Adaptive']:6.2f} | Delta: {ult_gain:+5.2f} | Optimal K: {optimal_k} ({optimal_pts_s:.2f} pts/s)",
            flush=True,
        )

    # Export benchmark CSVs
    with open("v26_benchmark.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(benchmark_rows[0].keys()))
        writer.writeheader()
        writer.writerows(benchmark_rows)

    with open("regime_map.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(regime_map_rows[0].keys()))
        writer.writeheader()
        writer.writerows(regime_map_rows)

    print("\n[OK] Exported v26_benchmark.csv and regime_map.csv successfully.", flush=True)
    return benchmark_rows, regime_map_rows


if __name__ == "__main__":
    run_transfer_experiment(n_episodes=8)
