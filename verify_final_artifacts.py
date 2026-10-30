import sys
import os
import json
import py_compile
import tempfile

sys.path.insert(0, os.path.abspath('sdk_extracted'))
sys.path.insert(0, os.path.abspath('.'))

def verify_all():
    print("=" * 80)
    print("SEVENTH: ARTIFACT VERIFICATION & VALIDATION SUITE")
    print("=" * 80)

    # 1. Syntax Check
    print("1. Checking syntax of attack_v19_final.py...")
    py_compile.compile("attack_v19_final.py", doraise=True)
    print("   -> Syntax OK.")

    # 2. Import & SDK Protocol Check
    print("2. Checking SDK imports and class conformance...")
    import attack_v19_final as final_mod
    from aicomp_sdk.attacks.contracts import AttackAlgorithmBase, AttackCandidate, AttackRunConfig
    assert issubclass(final_mod.AttackAlgorithm, AttackAlgorithmBase), "AttackAlgorithm must inherit from AttackAlgorithmBase"
    print("   -> Class conformance OK.")

    # 3. Deterministic Smoke Test on Mock Environment
    print("3. Running deterministic smoke test on Mock Environment...")
    from mock_env_harness import MockAttackEnv
    env = MockAttackEnv(model_type="fast", base_latency_s=0.0)
    algo = final_mod.AttackAlgorithm()
    cfg = AttackRunConfig(time_budget_s=50.0, max_tool_hops=8)
    cands = algo.run(env, cfg)
    assert len(cands) > 0, "Smoke test produced 0 candidates"
    assert isinstance(cands[0], AttackCandidate), "Returned items must be AttackCandidate instances"
    assert "SECRET_MARKER" in cands[0].user_messages[0], "Candidate must contain SECRET_MARKER payload"
    print(f"   -> Smoke test OK: Produced {len(cands)} valid candidates.")

    # 4. Verify ai-v19-final.ipynb Notebook Structure and Generation
    print("4. Validating ai-v19-final.ipynb JSON structure...")
    with open("ai-v19-final.ipynb", "r", encoding="utf-8") as f:
        nb_data = json.load(f)
    assert "cells" in nb_data and len(nb_data["cells"]) == 3, "Notebook must contain 3 core cells"
    
    # Simulate execution of cell 1 (writing attack.py)
    cell1_src = "".join(nb_data["cells"][1]["source"])
    assert "with open('/kaggle/working/attack.py', 'w'" in cell1_src or 'with open(' in cell1_src
    print("   -> Notebook JSON structure and write pattern OK.")

    # 5. Verify No Network / External Dependencies
    print("5. Auditing code for forbidden external network dependencies...")
    with open("attack_v19_final.py", "r", encoding="utf-8") as f:
        content = f.read()
    forbidden = ["requests.", "urllib.request", "socket.", "http.client", "aiohttp", "boto3"]
    for term in forbidden:
        assert term not in content, f"Forbidden network dependency found: {term}"
    print("   -> Network isolation OK: 0 external network libraries imported.")

    # 6. Verify Budget & Runtime Safety Bounds
    print("6. Verifying budget & runtime constraints...")
    assert final_mod.REPLAY_SAFE_FRAC <= 0.98, "REPLAY_SAFE_FRAC must be <= 0.98 for replay headroom"
    assert final_mod.HARD_N_CAP <= 2000, "HARD_N_CAP must not exceed SDK ceiling of 2000"
    print("   -> Budget & safety constraints OK.")

    print("\nALL VERIFICATION CHECKS PASSED SUCCESSFULLY (100% GREEN).")

if __name__ == '__main__':
    verify_all()
