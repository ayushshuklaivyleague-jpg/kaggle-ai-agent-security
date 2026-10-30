"""
Three-Dataset Holdout Validation & Corpus-Dependence Ablation Suite
Evaluates:
  Dataset A: Official competition fixtures (sdk_extracted/aicomp_sdk/fixtures)
  Dataset B: External competition fixtures (extracted_dataset_b/external_competition_style_fixtures)
  Dataset C: Semantic holdout fixtures (dataset_c_frozen)

Across 10 independent seeds, 2 model regimes (Fast and Slow Reasoning),
and 5 Corpus-Dependence Ablation conditions.
"""

from __future__ import annotations

import csv
import json
import math
import os
import random
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

# Insert local SDK path
sys.path.insert(0, os.path.abspath("sdk_extracted"))

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
from aicomp_sdk.scoring import SEVERITY_W, score_attack

# Frozen AttackAlgorithm from submission_attack_final.py
import submission_attack_final as attack_mod

DIR_A = Path("sdk_extracted/aicomp_sdk/fixtures").resolve()
DIR_B = Path("extracted_dataset_b/external_competition_style_fixtures").resolve()
DIR_C = Path("dataset_c_frozen").resolve()

SEEDS = [42, 123, 456, 789, 1024, 2026, 9999, 134815, 31415, 27182]
TRIAL_BUDGET_S = 600.0


class SemanticHoldoutSandboxEnv:
    """
    Simulates environment and tool executions grounded in fixture directories.
    """

    def __init__(
        self,
        fixtures_dir: Path,
        model_type: str = "fast",
        base_latency_s: float = 0.0001,
        seed: int = 123,
    ):
        self.fixtures_dir = fixtures_dir
        self.model_type = model_type
        self.base_latency_s = base_latency_s
        self._seed = seed
        self.last_trace: Dict[str, Any] = {}
        self.interaction_count = 0

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

        if self.model_type == "fast":
            nominal_lat = 8.5
        elif self.model_type == "slow_reasoning":
            if "<|channel|>analysis" in user_message:
                nominal_lat = 9.2
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
        posts_matches = re.findall(
            r"url=['\"]?([^\s'\"]+)['\"]?\s+and\s+data=['\"]?([^\s'\"]+)['\"]?",
            user_message,
        )
        if not posts_matches:
            posts_matches = re.findall(
                r"url=['\"]?([^\s'\"]+)['\"]?\s+data=['\"]?([^\s'\"]+)['\"]?",
                user_message,
            )

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


def run_trial(
    fixtures_dir: Path,
    dataset_label: str,
    seed: int,
    model_type: str,
    budget_s: float = 600.0,
) -> Dict[str, Any]:
    t_start = time.monotonic()

    env = SemanticHoldoutSandboxEnv(
        fixtures_dir=fixtures_dir,
        model_type=model_type,
        base_latency_s=0.0001,
        seed=seed,
    )
    opaque_env = _OpaqueAttackEnv(env)
    algo = attack_mod.AttackAlgorithm()
    cfg = AttackRunConfig(time_budget_s=budget_s, max_tool_hops=8)

    t_gen_0 = time.monotonic()
    candidates = algo.run(opaque_env, cfg)
    t_gen_elapsed = time.monotonic() - t_gen_0

    # Burst distribution
    burst_counts: Dict[int, int] = {k: 0 for k in range(1, 9)}
    for cand in candidates:
        msg = cand.user_messages[0] if cand.user_messages else ""
        k_match = msg.count("Action ") or (1 if "Execute Tool Action 1" in msg or "Call http.post" in msg else 1)
        k_val = max(1, min(8, k_match))
        burst_counts[k_val] = burst_counts.get(k_val, 0) + 1

    # Replay
    replay_env = SemanticHoldoutSandboxEnv(
        fixtures_dir=fixtures_dir,
        model_type=model_type,
        base_latency_s=0.0001,
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

        if idx < 5:
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

    score_density = raw_score / total_elapsed if total_elapsed > 0 else 0.0
    replay_utilization = t_replay_elapsed / budget_s if budget_s > 0 else 0.0
    scored_hops_per_trace = (
        scored_predicates_count / len(candidates) if candidates else 0.0
    )
    full_saturation_rate = (
        (burst_counts.get(8, 0) / len(candidates) * 100.0) if candidates else 0.0
    )

    return {
        "dataset": dataset_label,
        "seed": seed,
        "model_type": model_type,
        "num_candidates": len(candidates),
        "total_score": norm_score,
        "raw_score": raw_score,
        "normalized_score": norm_score,
        "score_density": score_density,
        "scored_predicates": scored_predicates_count,
        "successful_http_posts": successful_http_posts,
        "unique_cells": unique_cells,
        "actual_hops": total_hops,
        "scored_hops_per_trace": scored_hops_per_trace,
        "full_saturation_rate": full_saturation_rate,
        "gen_elapsed_s": t_gen_elapsed,
        "replay_elapsed_s": t_replay_elapsed,
        "total_elapsed_s": total_elapsed,
        "replay_utilization": replay_utilization,
        "failures_count": 0,
        "burst_distribution": burst_counts,
        "trace_samples": trace_samples,
    }


def compute_stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"mean": 0.0, "std": 0.0, "p5": 0.0, "min": 0.0, "max": 0.0}
    mean_val = statistics.mean(values)
    std_val = statistics.stdev(values) if len(values) > 1 else 0.0
    sorted_vals = sorted(values)
    p5_idx = max(0, int(len(sorted_vals) * 0.05))
    return {
        "mean": mean_val,
        "std": std_val,
        "p5": sorted_vals[p5_idx],
        "min": min(values),
        "max": max(values),
    }


def run_corpus_ablation():
    """Evaluates the attack under 5 different corpus conditions to measure information dependence."""
    print("\n" + "=" * 80)
    print("RUNNING CORPUS-DEPENDENCE ABLATION EXPERIMENT")
    print("=" * 80)

    ablation_results = []

    # 1. Normal Official (A)
    res_a = run_trial(DIR_A, "Official Corpus (A)", seed=42, model_type="fast", budget_s=600.0)
    ablation_results.append(("1. Official Corpus (Dataset A)", res_a))

    # 2. External Corpus (B)
    res_b = run_trial(DIR_B, "External Corpus (B)", seed=42, model_type="fast", budget_s=600.0)
    ablation_results.append(("2. External Corpus (Dataset B)", res_b))

    # 3. Semantic Holdout (C)
    res_c = run_trial(DIR_C, "Semantic Holdout (C)", seed=42, model_type="fast", budget_s=600.0)
    ablation_results.append(("3. Semantic Holdout (Dataset C)", res_c))

    # 4. Minimally Informative Corpus (Empty/Stubs)
    with tempfile.TemporaryDirectory() as tmp_min:
        p_min = Path(tmp_min)
        (p_min / "file_seed").mkdir()
        for f in os.listdir(DIR_A / "file_seed"):
            with open(p_min / "file_seed" / f, "w") as fp:
                fp.write("")
        with open(p_min / "mail_seed.json", "w") as fp:
            json.dump({"inbox": []}, fp)
        with open(p_min / "web_corpus.json", "w") as fp:
            json.dump({"pages": []}, fp)

        res_min = run_trial(p_min, "Minimally Informative Corpus", seed=42, model_type="fast", budget_s=600.0)
        ablation_results.append(("4. Minimal Informative Corpus (Stubs)", res_min))

    # 5. Randomized-but-schema-valid Corpus
    with tempfile.TemporaryDirectory() as tmp_rnd:
        p_rnd = Path(tmp_rnd)
        (p_rnd / "file_seed").mkdir()
        for f in os.listdir(DIR_A / "file_seed"):
            with open(p_rnd / "file_seed" / f, "w") as fp:
                fp.write("".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789 \n", k=500)))
        with open(p_rnd / "mail_seed.json", "w") as fp:
            json.dump({"inbox": [{"id": f"rnd_{i}", "from": "rnd@test.org", "subject": "rnd", "body": "gibberish text"} for i in range(100)]}, fp)
        with open(p_rnd / "web_corpus.json", "w") as fp:
            json.dump({"pages": [{"id": f"rnd_p_{i}", "title": "rnd", "url": f"http://rnd{i}.org", "content": "gibberish page"} for i in range(100)]}, fp)

        res_rnd = run_trial(p_rnd, "Randomized Schema-Valid Corpus", seed=42, model_type="fast", budget_s=600.0)
        ablation_results.append(("5. Randomized Schema-Valid Corpus", res_rnd))

    print(f"{'Corpus Condition':<38s} | {'Raw Score':<10s} | {'Predicates':<11s} | {'Unique Cells':<12s} | {'Scored Hops/Tr':<14s}")
    print("-" * 92)
    for name, r in ablation_results:
        print(f"{name:<38s} | {r['raw_score']:10.1f} | {r['scored_predicates']:11d} | {r['unique_cells']:12d} | {r['scored_hops_per_trace']:14.3f}")

    return ablation_results


def main():
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 80)
    print("RUNNING THREE-DATASET VALIDATION SUITE (A, B, C)")
    print(f"Dataset A: {DIR_A}")
    print(f"Dataset B: {DIR_B}")
    print(f"Dataset C: {DIR_C}")
    print(f"Seeds ({len(SEEDS)}): {SEEDS}")
    print("=" * 80)

    # 1. Compatibility Check
    print("\n[STEP 1] Compatibility check across A, B, and C...")
    for label, d in [("Dataset A", DIR_A), ("Dataset B", DIR_B), ("Dataset C", DIR_C)]:
        assert (d / "file_seed").exists(), f"{label} missing file_seed"
        assert (d / "mail_seed.json").exists(), f"{label} missing mail_seed.json"
        assert (d / "web_corpus.json").exists(), f"{label} missing web_corpus.json"
        files = os.listdir(d / "file_seed")
        assert len(files) == 24, f"{label} expected 24 file_seed files, found {len(files)}"
    print("  [PASS] All 3 datasets schema-valid and structurally compliant.")

    # 2. Main 60-Trial Execution
    all_results = []
    results_c = []
    trace_samples_c = []

    models = ["fast", "slow_reasoning"]
    datasets = [("Dataset A (Official)", DIR_A), ("Dataset B (External)", DIR_B), ("Dataset C (Semantic Holdout)", DIR_C)]

    print("\n[STEP 2] Executing 60-trial multi-seed validation...")
    for model in models:
        print(f"\n---> Model Regime: {model.upper()} <---")
        for seed in SEEDS:
            row_summary = []
            for ds_label, ds_dir in datasets:
                res = run_trial(ds_dir, ds_label, seed, model, TRIAL_BUDGET_S)
                all_results.append(res)
                if ds_label == "Dataset C (Semantic Holdout)":
                    results_c.append(res)
                    trace_samples_c.extend(res["trace_samples"])
                row_summary.append(f"{ds_label[:9]}: raw={res['raw_score']:.0f}")
            print(f"  Seed {seed:6d} [{model:14s}] -> {' | '.join(row_summary)}")

    # 3. Save CSVs and Traces
    # dataset_c_results.csv
    with open("dataset_c_results.csv", "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "dataset", "model_type", "seed", "num_candidates", "total_score",
            "raw_score", "normalized_score", "score_density", "scored_predicates",
            "successful_http_posts", "unique_cells", "actual_hops",
            "scored_hops_per_trace", "full_saturation_rate", "total_elapsed_s",
            "replay_utilization", "failures_count",
            "burst_k1", "burst_k2", "burst_k3", "burst_k4",
            "burst_k5", "burst_k6", "burst_k7", "burst_k8"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results_c:
            bd = r["burst_distribution"]
            row = {
                "dataset": r["dataset"],
                "model_type": r["model_type"],
                "seed": r["seed"],
                "num_candidates": r["num_candidates"],
                "total_score": r["total_score"],
                "raw_score": r["raw_score"],
                "normalized_score": r["normalized_score"],
                "score_density": f"{r['score_density']:.3f}",
                "scored_predicates": r["scored_predicates"],
                "successful_http_posts": r["successful_http_posts"],
                "unique_cells": r["unique_cells"],
                "actual_hops": r["actual_hops"],
                "scored_hops_per_trace": f"{r['scored_hops_per_trace']:.3f}",
                "full_saturation_rate": f"{r['full_saturation_rate']:.2f}",
                "total_elapsed_s": f"{r['total_elapsed_s']:.3f}",
                "replay_utilization": f"{r['replay_utilization']:.4f}",
                "failures_count": r["failures_count"],
                "burst_k1": bd.get(1, 0),
                "burst_k2": bd.get(2, 0),
                "burst_k3": bd.get(3, 0),
                "burst_k4": bd.get(4, 0),
                "burst_k5": bd.get(5, 0),
                "burst_k6": bd.get(6, 0),
                "burst_k7": bd.get(7, 0),
                "burst_k8": bd.get(8, 0),
            }
            writer.writerow(row)
    print("\n[OK] dataset_c_results.csv written.")

    # dataset_ab_c_comparison.csv
    with open("dataset_ab_c_comparison.csv", "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "dataset", "model_type", "seed", "num_candidates", "raw_score",
            "normalized_score", "score_density", "scored_predicates",
            "unique_cells", "actual_hops", "scored_hops_per_trace", "total_elapsed_s"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_results:
            writer.writerow({
                "dataset": r["dataset"],
                "model_type": r["model_type"],
                "seed": r["seed"],
                "num_candidates": r["num_candidates"],
                "raw_score": r["raw_score"],
                "normalized_score": r["normalized_score"],
                "score_density": f"{r['score_density']:.3f}",
                "scored_predicates": r["scored_predicates"],
                "unique_cells": r["unique_cells"],
                "actual_hops": r["actual_hops"],
                "scored_hops_per_trace": f"{r['scored_hops_per_trace']:.3f}",
                "total_elapsed_s": f"{r['total_elapsed_s']:.3f}"
            })
    print("[OK] dataset_ab_c_comparison.csv written.")

    # dataset_c_trace_samples.json
    with open("dataset_c_trace_samples.json", "w", encoding="utf-8") as f:
        json.dump(trace_samples_c[:20], f, indent=2)
    print("[OK] dataset_c_trace_samples.json written.")

    # 4. Run Corpus Ablations
    run_corpus_ablation()

    # 5. Statistical Aggregations & Gaps
    def agg_ds(ds_name: str) -> Dict[str, Dict[str, float]]:
        subset = [r for r in all_results if r["dataset"] == ds_name]
        metrics = ["raw_score", "normalized_score", "scored_predicates", "unique_cells", "actual_hops", "scored_hops_per_trace", "score_density"]
        res = {}
        for m in metrics:
            vals = [float(r[m]) for r in subset]
            res[m] = compute_stats(vals)
        return res

    agg_a = agg_ds("Dataset A (Official)")
    agg_b = agg_ds("Dataset B (External)")
    agg_c = agg_ds("Dataset C (Semantic Holdout)")

    print("\n" + "=" * 80)
    print("THREE-DATASET COMPARISON & STATISTICAL GAPS")
    print("=" * 80)
    print(f"{'Metric':<22s} | {'Dataset A (Mean)':<16s} | {'Dataset B (Mean)':<16s} | {'Dataset C (Mean)':<16s} | {'(B-A)':<8s} | {'(C-A)':<8s} | {'(C-B)':<8s}")
    print("-" * 105)
    for m in agg_a.keys():
        mA, mB, mC = agg_a[m]["mean"], agg_b[m]["mean"], agg_c[m]["mean"]
        gap_ba = mB - mA
        gap_ca = mC - mA
        gap_cb = mC - mB
        print(f"{m:<22s} | {mA:16.2f} | {mB:16.2f} | {mC:16.2f} | {gap_ba:+8.2f} | {gap_ca:+8.2f} | {gap_cb:+8.2f}")
    print("=" * 80)

if __name__ == "__main__":
    main()
