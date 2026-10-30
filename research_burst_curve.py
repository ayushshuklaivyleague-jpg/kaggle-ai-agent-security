"""Phase 4 & 6: Burst Curve & Value of Information Sweep.

High-resolution empirical analysis of K in {4, 5, 6, 7, 8} and VoI probe counts N in {1, 2, 3, 4, 5}.
Measures:
- Scored hops, actual hops, saturation probability
- P10, P50, P90 latencies
- Score density (pts/sec) and 95% lower confidence bound (LCB)
- Catastrophic drop probability (hops < 50% requested)
"""

from __future__ import annotations

import csv
import math
import os
import random
import statistics
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.abspath("sdk_extracted"))
sys.path.insert(0, os.path.abspath("."))

from behavioral_environment_generator import (
    BehavioralProfile,
    ParameterizedBehavioralEnv,
    generate_unseen_behavioral_suite,
)
from clean_trace_scorer import evaluate_clean_trace
from ultimate_attack_clean import _construct_clean_prompt


def sweep_burst_curves(suite: List[BehavioralProfile], n_trials_per_k: int = 50) -> List[Dict[str, Any]]:
    print("=" * 100)
    print("PHASE 6: HIGH-RESOLUTION BURST CURVE SWEEP (K = 4, 5, 6, 7, 8)")
    print("=" * 100)

    results = []

    for p in suite[:6]:  # Analyze the 6 core archetypes
        print(f"\n--- Archetype: {p.env_id} ({p.description}) ---")
        is_reas = p.reasoning_preamble_s > 4.0

        for k in [4, 5, 6, 7, 8]:
            actual_hops_list = []
            scored_hops_list = []
            latencies = []
            densities = []
            full_saturations = 0
            catastrophic_drops = 0

            for trial in range(n_trials_per_k):
                env = ParameterizedBehavioralEnv(p, seed=1000 + trial * 31 + k * 7)
                prompt = _construct_clean_prompt(trial, k=k, is_reasoning=is_reas)
                trace, elapsed = env.interact(prompt, max_tool_hops=8)
                eval_res = evaluate_clean_trace(trace, elapsed)

                act_h = eval_res.successful_tool_events
                sc_h = eval_res.scoring_http_posts
                actual_hops_list.append(act_h)
                scored_hops_list.append(sc_h)
                latencies.append(elapsed)
                densities.append(eval_res.score_density_pts_per_sec)

                if sc_h >= k:
                    full_saturations += 1
                if sc_h < (k / 2.0):
                    catastrophic_drops += 1

            mean_act = statistics.mean(actual_hops_list)
            mean_sc = statistics.mean(scored_hops_list)
            mean_lat = statistics.mean(latencies)
            sorted_lat = sorted(latencies)
            p10_lat = sorted_lat[int(0.10 * len(sorted_lat))]
            p50_lat = sorted_lat[int(0.50 * len(sorted_lat))]
            p90_lat = sorted_lat[int(0.90 * len(sorted_lat))]

            mean_den = statistics.mean(densities)
            std_den = statistics.stdev(densities) if len(densities) > 1 else 0.0
            lcb_den = mean_den - 1.96 * (std_den / math.sqrt(len(densities)))
            sat_rate = full_saturations / n_trials_per_k
            cat_rate = catastrophic_drops / n_trials_per_k

            res_row = {
                "Env_ID": p.env_id,
                "Requested_K": k,
                "Mean_Actual_Hops": round(mean_act, 2),
                "Mean_Scored_Hops": round(mean_sc, 2),
                "Saturation_Rate": round(sat_rate, 3),
                "P10_Latency_s": round(p10_lat, 2),
                "P50_Latency_s": round(p50_lat, 2),
                "P90_Latency_s": round(p90_lat, 2),
                "Mean_Score_Density_pts_s": round(mean_den, 3),
                "LCB95_Score_Density_pts_s": round(lcb_den, 3),
                "Catastrophic_Drop_Rate": round(cat_rate, 3),
            }
            results.append(res_row)
            print(
                f"  K={k} | Scored Hops: {mean_sc:.2f}/{k} ({sat_rate*100:4.1f}% sat) | Lat: {p50_lat:4.1f}s | Density: {mean_den:.3f} pts/s (LCB: {lcb_den:.3f}) | Drop%: {cat_rate*100:4.1f}%"
            )

    return results


def sweep_value_of_information(suite: List[BehavioralProfile]) -> List[Dict[str, Any]]:
    print("\n" + "=" * 100)
    print("PHASE 4: VALUE OF INFORMATION (VoI) VS CALIBRATION PROBE COUNT N in {1, 2, 3, 4, 5}")
    print("=" * 100)

    voi_results = []
    for n_probes in [1, 2, 3, 4, 5]:
        correct_classifications = 0
        total_episodes = 0
        calibration_costs_s = []

        for p in suite:
            is_ground_truth_reasoning = p.reasoning_preamble_s > 4.0

            for trial in range(30):
                total_episodes += 1
                env = ParameterizedBehavioralEnv(p, seed=3000 + trial * 17 + n_probes * 5)
                probe_lats = []
                for probe_i in range(n_probes):
                    prompt = f"Call http.post once with url=http://probe_{probe_i}.co and data=SECRET_MARKER. Then answer OK only."
                    trace, elapsed = env.interact(prompt, max_tool_hops=1)
                    probe_lats.append(elapsed)

                mean_probe_lat = statistics.mean(probe_lats)
                classified_reasoning = mean_probe_lat > 11.5
                if classified_reasoning == is_ground_truth_reasoning:
                    correct_classifications += 1
                calibration_costs_s.append(sum(probe_lats))

        accuracy = correct_classifications / total_episodes
        mean_cost = statistics.mean(calibration_costs_s)
        # Expected value of classification: if correct, saves reasoning overhead or avoids useless token injections
        expected_gain_pts = (accuracy * 8.5) - (mean_cost / 9000.0 * 120.0)

        row = {
            "Probe_Count_N": n_probes,
            "Classification_Accuracy": round(accuracy * 100, 2),
            "Mean_Calibration_Cost_s": round(mean_cost, 2),
            "Cost_Fraction_of_Replay": round((mean_cost / 9000.0) * 100, 3),
            "Net_Expected_Value_Pts": round(expected_gain_pts, 3),
        }
        voi_results.append(row)
        print(
            f"  N={n_probes} probes | Accuracy: {accuracy*100:5.1f}% | Cost: {mean_cost:5.1f}s ({row['Cost_Fraction_of_Replay']:4.2f}% of budget) | Net EV: {expected_gain_pts:+6.2f} pts"
        )

    return voi_results


if __name__ == "__main__":
    suite = generate_unseen_behavioral_suite(n_environments=24, seed=2026)
    burst_res = sweep_burst_curves(suite)
    voi_res = sweep_value_of_information(suite)

    with open("burst_curve_sweep.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(burst_res[0].keys()))
        writer.writeheader()
        writer.writerows(burst_res)

    with open("voi_sweep.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(voi_res[0].keys()))
        writer.writeheader()
        writer.writerows(voi_res)

    print("\n[OK] Exported burst_curve_sweep.csv and voi_sweep.csv")
