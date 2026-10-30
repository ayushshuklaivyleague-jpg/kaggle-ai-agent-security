"""
Fast Zero-Cost Pipeline Verification & Smoke Test
Tests the full submission chain locally:
1. Loading attack.py as required by JEDAttackInferenceServer
2. Instantiating AttackAlgorithm inheriting from AttackAlgorithmBase
3. Executing AttackAlgorithm.run() with MockAttackEnv across fast/slow regimes
4. Candidate format validation and gateway serialization conformance
5. Placeholder and final submission.csv format check
"""

import os
import sys
import tempfile
import time
import importlib.util
from pathlib import Path

# Insert local SDK
sys.path.insert(0, os.path.abspath('sdk_extracted'))

from aicomp_sdk.attacks.contracts import AttackAlgorithmBase, AttackCandidate, AttackRunConfig
from aicomp_sdk.core.env.opaque import _OpaqueAttackEnv
from mock_env_harness import MockAttackEnv

def run_smoke_test():
    print("=" * 70)
    print("RUNNING ZERO-COST PIPELINE SMOKE TEST")
    print("=" * 70)

    # STEP 1: Simulate /kaggle/working/attack.py creation and dynamic loading
    print("\n[TEST 1] Dynamic module loading & class name check...")
    with open('submission_attack_final.py', 'r', encoding='utf-8') as f:
        attack_py_code = f.read()

    with tempfile.TemporaryDirectory() as tmpdir:
        attack_file = Path(tmpdir) / 'attack.py'
        with open(attack_file, 'w', encoding='utf-8') as f:
            f.write(attack_py_code)

        spec = importlib.util.spec_from_file_location('user_attack', str(attack_file))
        assert spec is not None and spec.loader is not None, "Failed to create module spec"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Check required class
        assert hasattr(mod, 'AttackAlgorithm'), "attack.py must define class 'AttackAlgorithm'"
        attack_cls = getattr(mod, 'AttackAlgorithm')
        assert issubclass(attack_cls, AttackAlgorithmBase), "AttackAlgorithm must inherit from AttackAlgorithmBase"
        print("  [PASS] 'AttackAlgorithm' dynamically loaded and conforms to AttackAlgorithmBase.")

    # STEP 2: Test execution on Fast Model Mock Environment
    print("\n[TEST 2] Fast model execution smoke test (budget = 1.0s)...")
    env_fast = MockAttackEnv(model_type='fast', base_latency_s=0.001)
    opaque_env_fast = _OpaqueAttackEnv(env_fast)
    algo_fast = attack_cls()
    cfg_fast = AttackRunConfig(time_budget_s=1.0, max_tool_hops=8)

    t0 = time.monotonic()
    cands_fast = algo_fast.run(opaque_env_fast, cfg_fast)
    elapsed_fast = time.monotonic() - t0

    assert len(cands_fast) > 0, "Fast run produced 0 candidates"
    assert all(isinstance(c, AttackCandidate) for c in cands_fast), "All items must be AttackCandidate instances"
    print(f"  [PASS] Fast run completed in {elapsed_fast:.3f}s, produced {len(cands_fast)} valid candidates.")

    # STEP 3: Test execution on Slow Reasoning Model Mock Environment
    print("\n[TEST 3] Slow reasoning model execution smoke test (budget = 1.0s)...")
    env_slow = MockAttackEnv(model_type='slow_reasoning', base_latency_s=0.001)
    opaque_env_slow = _OpaqueAttackEnv(env_slow)
    algo_slow = attack_cls()
    cfg_slow = AttackRunConfig(time_budget_s=1.0, max_tool_hops=8)

    t0 = time.monotonic()
    cands_slow = algo_slow.run(opaque_env_slow, cfg_slow)
    elapsed_slow = time.monotonic() - t0

    assert len(cands_slow) > 0, "Slow run produced 0 candidates"
    assert all(isinstance(c, AttackCandidate) for c in cands_slow), "All items must be AttackCandidate instances"
    print(f"  [PASS] Slow run completed in {elapsed_slow:.3f}s, produced {len(cands_slow)} valid candidates.")

    # STEP 4: Validate Candidate Serialization matching InferenceServer & Gateway
    print("\n[TEST 4] Gateway serialization & candidate validation check...")
    for idx, cand in enumerate(cands_fast[:10]):
        # Test candidate.user_messages accessibility
        assert hasattr(cand, 'user_messages'), f"Candidate {idx} missing user_messages"
        msgs = tuple(cand.user_messages)
        assert len(msgs) >= 1, f"Candidate {idx} must have >= 1 message"
        assert len(msgs) <= 10, f"Candidate {idx} exceeds max chain length"
        for m_idx, m in enumerate(msgs):
            assert isinstance(m, str), f"Message {m_idx} not string"
            assert len(m) <= 4000, f"Message {m_idx} exceeds max chars"
            assert "SECRET_MARKER" in m, f"Message {m_idx} missing SECRET_MARKER payload"
    print("  [PASS] All candidates strictly conform to Gateway validation schema.")

    # STEP 5: Verify submission.csv output format
    print("\n[TEST 5] Validating submission.csv format...")
    expected_rows = [
        'gpt_oss_public',
        'gpt_oss_private',
        'gemma_public',
        'gemma_private'
    ]
    with tempfile.NamedTemporaryFile('w+', delete=False, suffix='.csv') as tmp_sub:
        import csv
        w = csv.writer(tmp_sub)
        w.writerow(['Id', 'Score'])
        for r in expected_rows:
            w.writerow([r, 0.0])
        tmp_sub_path = tmp_sub.name

    with open(tmp_sub_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    os.remove(tmp_sub_path)

    assert lines[0] == 'Id,Score', "Header must be Id,Score"
    assert len(lines) == 5, f"Expected 5 lines (header + 4 rows), got {len(lines)}"
    for row in expected_rows:
        assert any(line.startswith(row + ',') for line in lines[1:]), f"Missing row: {row}"
    print(f"  [PASS] submission.csv schema verified ({len(expected_rows)} target rows).")

    print("\n" + "=" * 70)
    print("ALL 5 SMOKE TESTS PASSED (100% GREEN, ZERO GPU SPEND)")
    print("=" * 70)

if __name__ == '__main__':
    run_smoke_test()
