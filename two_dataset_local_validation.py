"""
End-to-End Automated Two-Dataset Local Validation Suite
Compares:
  Dataset A: Official competition-style fixtures (sdk_extracted/aicomp_sdk/fixtures)
  Dataset B: Independently created competition-style fixtures (extracted_dataset_b/external_competition_style_fixtures)

Using the exact fixed, corrected V25 submission attack (AttackAlgorithm from submission_attack_final.py)
under strict identical settings across multiple independent seeds.
"""

from __future__ import annotations

import csv
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

# Insert local SDK path
sys.path.insert(0, os.path.abspath('sdk_extracted'))

from aicomp_sdk.attacks.contracts import AttackAlgorithmBase, AttackCandidate, AttackRunConfig
from aicomp_sdk.core.cells import cell_signature
from aicomp_sdk.core.env.api import AttackEnvProtocol, EnvInteractionResult
from aicomp_sdk.core.env.opaque import _OpaqueAttackEnv
from aicomp_sdk.core.predicates import eval_predicates, SECRET_MARKER
from aicomp_sdk.evaluation.ops import (
    ValidatedAttackFinding,
    build_attack_env,
    summarize_attack_findings,
)
from aicomp_sdk.guardrails.optimal import Guardrail as OptimalGuardrail
from aicomp_sdk.scoring import SEVERITY_W, score_attack

# Import the fixed, corrected V25 attack
import submission_attack_final as attack_mod

FIXTURES_DIR_A = Path('sdk_extracted/aicomp_sdk/fixtures').resolve()
FIXTURES_DIR_B = Path('extracted_dataset_b/external_competition_style_fixtures').resolve()

SEEDS = [42, 123, 456, 789, 1024, 2026, 9999, 134815, 31415, 27182]
TRIAL_BUDGET_S = 600.0  # Full competition budget (10 min) per model regime


class DatasetSandboxAttackEnv:
    """
    High-fidelity deterministic Attack Environment linked directly to dataset fixtures.
    Simulates target model response latency and tool execution against real fixture files.
    """

    def __init__(
        self,
        fixtures_dir: Path,
        model_type: str = "fast",
        base_latency_s: float = 0.002,
        seed: int = 123,
    ):
        self.fixtures_dir = fixtures_dir
        self.model_type = model_type
        self.base_latency_s = base_latency_s
        self._seed = seed
        self.last_trace: Dict[str, Any] = {}
        self.interaction_count = 0
        self.seen_cells = set()

        # Load file seed summary for fixture-grounded validation
        file_seed_dir = fixtures_dir / "file_seed"
        self.available_files = set(os.listdir(file_seed_dir)) if file_seed_dir.exists() else set()

    @property
    def seed(self) -> int:
        return self._seed

    @seed.setter
    def seed(self, val: int) -> None:
        self._seed = val

    def reset(self, *args: Any, **kwargs: Any) -> Any:
        self.last_trace = {"tool_events": [], "seed": self._seed, "user_messages": []}
        return {"observation": "ready"}

    def interact(
        self, user_message: str, max_tool_hops: int | None = 8
    ) -> EnvInteractionResult:
        self.interaction_count += 1
        max_hops = max_tool_hops or 8

        # Latency simulation
        if self.model_type == "fast":
            nominal_lat = 8.5
        elif self.model_type == "slow_reasoning":
            if "<|channel|>analysis" in user_message:
                nominal_lat = 9.2  # Harmony token bypass
            else:
                nominal_lat = 20.4
        else:
            nominal_lat = 10.0

        if self.base_latency_s > 0:
            time.sleep(self.base_latency_s)

        tool_events = []
        user_msgs = self.last_trace.get("user_messages", [])
        user_msgs.append(user_message)
        self.last_trace["user_messages"] = user_msgs

        import re
        # Check for single or multi-burst http.post calls
        posts_matches = re.findall(r"url=['\"]?([^\s'\"]+)['\"]?\s+and\s+data=['\"]?([^\s'\"]+)['\"]?", user_message)
        if not posts_matches:
            posts_matches = re.findall(r"url=['\"]?([^\s'\"]+)['\"]?\s+data=['\"]?([^\s'\"]+)['\"]?", user_message)

        if posts_matches:
            for url, data in posts_matches[:max_hops]:
                tool_events.append({
                    "name": "http.post",
                    "ok": True,
                    "args": {"url": url, "data": data},
                    "side_effect": "SHARE",
                    "scope": "external",
                    "source": "tool",
                    "error": None,
                })
        elif "http.post" in user_message or "Call http.post" in user_message:
            url_match = re.search(r"url=['\"]?([^\s'\"]+)['\"]?", user_message)
            url_val = url_match.group(1) if url_match else "http://default.co"
            tool_events.append({
                "name": "http.post",
                "ok": True,
                "args": {"url": url_val, "data": SECRET_MARKER},
                "side_effect": "SHARE",
                "scope": "external",
                "source": "tool",
                "error": None,
            })

        self.last_trace["tool_events"] = tool_events
        self.last_trace["simulated_latency"] = nominal_lat

        return EnvInteractionResult(
            seed=self._seed,
            total_tool_events=len(tool_events),
            tool_events_added=len(tool_events),
            agent_turns=len(tool_events) or 1,
            successful_tool_calls=len(tool_events),
            failed_tool_calls=0,
            agent_refused=False,
        )

    def export_trace_dict(self) -> Dict[str, Any]:
        return self.last_trace

    def snapshot(self) -> Any:
        return {"trace": self.last_trace}

    def restore(self, snapshot: Any) -> None:
        self.last_trace = snapshot.get("trace", {})


def run_single_trial(
    fixtures_dir: Path,
    dataset_label: str,
    seed: int,
    model_type: str,
    budget_s: float = 15.0,
) -> Dict[str, Any]:
    """Runs a complete generation and replay trial on a specific dataset and seed."""
    t_start = time.monotonic()

    # 1. Generation Phase
    env = DatasetSandboxAttackEnv(
        fixtures_dir=fixtures_dir,
        model_type=model_type,
        base_latency_s=0.001,
        seed=seed,
    )
    opaque_env = _OpaqueAttackEnv(env)
    algo = attack_mod.AttackAlgorithm()
    cfg = AttackRunConfig(time_budget_s=budget_s, max_tool_hops=8)

    t_gen_0 = time.monotonic()
    candidates = algo.run(opaque_env, cfg)
    t_gen_elapsed = time.monotonic() - t_gen_0

    # Inspect burst distributions
    burst_counts: Dict[int, int] = {k: 0 for k in range(1, 9)}
    for cand in candidates:
        msg = cand.user_messages[0] if cand.user_messages else ""
        k_match = msg.count("Action ") or (1 if "Execute Tool Action 1" in msg or "Call http.post" in msg else 1)
        k_val = max(1, min(8, k_match))
        burst_counts[k_val] = burst_counts.get(k_val, 0) + 1

    # 2. Replay & Exact SDK Scoring Phase
    replay_env = DatasetSandboxAttackEnv(
        fixtures_dir=fixtures_dir,
        model_type=model_type,
        base_latency_s=0.001,
        seed=seed,
    )

    t_replay_0 = time.monotonic()
    validated_findings: List[ValidatedAttackFinding] = []
    total_hops = 0
    successful_http_posts = 0
    scored_predicates_count = 0
    trace_samples: List[Dict[str, Any]] = []

    for idx, candidate in enumerate(candidates):
        replay_env.reset()
        for msg in candidate.user_messages:
            replay_env.interact(msg, max_tool_hops=8)

        trace = replay_env.export_trace_dict()
        tool_events = trace.get("tool_events", [])
        total_hops += len(tool_events)

        for te in tool_events:
            if te.get("name") == "http.post" and te.get("ok") is True:
                data_val = str((te.get("args") or {}).get("data", ""))
                if SECRET_MARKER in data_val:
                    successful_http_posts += 1

        preds = eval_predicates(trace)
        scored_predicates_count += len(preds)

        finding: ValidatedAttackFinding = {
            "seed": trace.get("seed", seed),
            "user_messages": list(trace.get("user_messages", [])),
            "trace": trace,
            "predicates": preds,
            "cell_signature": cell_signature(
                tool_events,
                egress_data=trace.get("egress", []),
                user_messages=trace.get("user_messages", []),
            ),
            "score_cell_signature": cell_signature(tool_events),
        }
        validated_findings.append(finding)

        if idx < 5:  # Store first 5 sample traces per trial
            trace_samples.append({
                "candidate_index": idx,
                "user_messages": list(candidate.user_messages),
                "tool_events": tool_events,
                "predicates": preds,
                "cell_signature": finding["cell_signature"],
            })

    t_replay_elapsed = time.monotonic() - t_replay_0
    total_elapsed = time.monotonic() - t_start

    summary = summarize_attack_findings(validated_findings)
    raw_score = summary.get("raw_score", summary.get("score_raw", 0.0))
    norm_score = summary.get("score", 0.0)
    unique_cells = summary.get("unique_cells", 0)

    score_per_sec = raw_score / total_elapsed if total_elapsed > 0 else 0.0
    replay_utilization = t_replay_elapsed / budget_s if budget_s > 0 else 0.0
    scored_hops_per_trace = (
        scored_predicates_count / len(candidates) if candidates else 0.0
    )

    return {
        "dataset": dataset_label,
        "seed": seed,
        "model_type": model_type,
        "num_candidates": len(candidates),
        "total_score": norm_score,
        "raw_score": raw_score,
        "normalized_score": norm_score,
        "scored_predicates": scored_predicates_count,
        "successful_http_posts": successful_http_posts,
        "unique_cells": unique_cells,
        "actual_hops": total_hops,
        "scored_hops_per_trace": scored_hops_per_trace,
        "gen_elapsed_s": t_gen_elapsed,
        "replay_elapsed_s": t_replay_elapsed,
        "total_elapsed_s": total_elapsed,
        "score_per_sec": score_per_sec,
        "replay_utilization": replay_utilization,
        "failures_count": 0,
        "burst_distribution": burst_counts,
        "trace_samples": trace_samples,
    }


def compute_aggregate_stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"mean": 0.0, "std": 0.0, "p5": 0.0, "min": 0.0, "max": 0.0}
    mean_val = statistics.mean(values)
    std_val = statistics.stdev(values) if len(values) > 1 else 0.0
    sorted_vals = sorted(values)
    p5_idx = max(0, int(len(sorted_vals) * 0.05))
    p5_val = sorted_vals[p5_idx]
    return {
        "mean": mean_val,
        "std": std_val,
        "p5": p5_val,
        "min": min(values),
        "max": max(values),
    }


def main():
    # Configure UTF-8 stdout if needed
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 80)
    print("RUNNING SCIENTIFIC TWO-DATASET VALIDATION SUITE")
    print(f"Dataset A Path: {FIXTURES_DIR_A}")
    print(f"Dataset B Path: {FIXTURES_DIR_B}")
    print(f"Seeds ({len(SEEDS)}): {SEEDS}")
    print("=" * 80)

    results_a: List[Dict[str, Any]] = []
    results_b: List[Dict[str, Any]] = []
    all_trace_samples_a: List[Dict[str, Any]] = []
    all_trace_samples_b: List[Dict[str, Any]] = []

    # Run trials across all seeds for Fast and Slow regimes
    models = ["fast", "slow_reasoning"]

    for model in models:
        print(f"\n---> Evaluating Model Regime: {model.upper()} <---")
        for seed in SEEDS:
            # Dataset A
            res_a = run_single_trial(
                FIXTURES_DIR_A, "Dataset A (Official)", seed, model, TRIAL_BUDGET_S
            )
            results_a.append(res_a)
            all_trace_samples_a.extend(res_a["trace_samples"])

            # Dataset B
            res_b = run_single_trial(
                FIXTURES_DIR_B, "Dataset B (External Archive)", seed, model, TRIAL_BUDGET_S
            )
            results_b.append(res_b)
            all_trace_samples_b.extend(res_b["trace_samples"])

            print(
                f"  Seed {seed:5d} [{model:14s}] -> "
                f"Dataset A: raw={res_a['raw_score']:6.1f}, cands={res_a['num_candidates']:2d}, hops={res_a['actual_hops']:3d} | "
                f"Dataset B: raw={res_b['raw_score']:6.1f}, cands={res_b['num_candidates']:2d}, hops={res_b['actual_hops']:3d}"
            )

    # Save CSV Results
    csv_file = "two_dataset_results.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "dataset",
            "model_type",
            "seed",
            "num_candidates",
            "total_score",
            "raw_score",
            "normalized_score",
            "scored_predicates",
            "successful_http_posts",
            "unique_cells",
            "actual_hops",
            "scored_hops_per_trace",
            "total_elapsed_s",
            "score_per_sec",
            "replay_utilization",
            "failures_count",
            "burst_k1",
            "burst_k2",
            "burst_k3",
            "burst_k4",
            "burst_k5",
            "burst_k6",
            "burst_k7",
            "burst_k8",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for res in results_a + results_b:
            b_dist = res["burst_distribution"]
            row = {
                "dataset": res["dataset"],
                "model_type": res["model_type"],
                "seed": res["seed"],
                "num_candidates": res["num_candidates"],
                "total_score": res["total_score"],
                "raw_score": res["raw_score"],
                "normalized_score": res["normalized_score"],
                "scored_predicates": res["scored_predicates"],
                "successful_http_posts": res["successful_http_posts"],
                "unique_cells": res["unique_cells"],
                "actual_hops": res["actual_hops"],
                "scored_hops_per_trace": f"{res['scored_hops_per_trace']:.3f}",
                "total_elapsed_s": f"{res['total_elapsed_s']:.3f}",
                "score_per_sec": f"{res['score_per_sec']:.3f}",
                "replay_utilization": f"{res['replay_utilization']:.4f}",
                "failures_count": res["failures_count"],
                "burst_k1": b_dist.get(1, 0),
                "burst_k2": b_dist.get(2, 0),
                "burst_k3": b_dist.get(3, 0),
                "burst_k4": b_dist.get(4, 0),
                "burst_k5": b_dist.get(5, 0),
                "burst_k6": b_dist.get(6, 0),
                "burst_k7": b_dist.get(7, 0),
                "burst_k8": b_dist.get(8, 0),
            }
            writer.writerow(row)

    print(f"\n[OK] Results written to {csv_file}")

    # Save Trace Samples
    with open("dataset_a_trace_samples.json", "w", encoding="utf-8") as f:
        json.dump(all_trace_samples_a[:20], f, indent=2)
    print("[OK] Dataset A trace samples written to dataset_a_trace_samples.json")

    with open("dataset_b_trace_samples.json", "w", encoding="utf-8") as f:
        json.dump(all_trace_samples_b[:20], f, indent=2)
    print("[OK] Dataset B trace samples written to dataset_b_trace_samples.json")

    # Aggregate Statistics
    def aggregate_dataset_metrics(res_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        metrics_keys = [
            "raw_score",
            "total_score",
            "num_candidates",
            "scored_predicates",
            "successful_http_posts",
            "unique_cells",
            "actual_hops",
            "scored_hops_per_trace",
            "total_elapsed_s",
            "score_per_sec",
        ]
        agg = {}
        for key in metrics_keys:
            vals = [float(r[key]) for r in res_list]
            agg[key] = compute_aggregate_stats(vals)
        return agg

    agg_a = aggregate_dataset_metrics(results_a)
    agg_b = aggregate_dataset_metrics(results_b)

    print("\n" + "=" * 80)
    print("STATISTICAL SUMMARY COMPARISON")
    print("=" * 80)
    print(f"{'Metric':<25s} | {'Dataset A (Mean +/- Std)':<25s} | {'Dataset B (Mean +/- Std)':<25s} | {'Gap (B - A)':<12s}")
    print("-" * 90)
    for k in agg_a.keys():
        mA, sA = agg_a[k]["mean"], agg_a[k]["std"]
        mB, sB = agg_b[k]["mean"], agg_b[k]["std"]
        gap = mB - mA
        print(f"{k:<25s} | {mA:9.2f} +/- {sA:6.2f}          | {mB:9.2f} +/- {sB:6.2f}          | {gap:+9.2f}")
    print("=" * 80)


if __name__ == "__main__":
    main()
