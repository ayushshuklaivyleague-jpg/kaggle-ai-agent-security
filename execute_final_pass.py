import sys
import os
import time
import statistics

sys.path.insert(0, os.path.abspath('sdk_extracted'))
sys.path.insert(0, os.path.abspath('.'))

from run_statistical_eval import run_trials
import extracted_v15 as attack_v15
import attack_v19_final as attack_v19_prod

def run_all_phases():
    print("=" * 95)
    print("PHASE 2: APPLES-TO-APPLES BENCHMARK (10 Repeated Stochastic Trials per Condition)")
    print("=" * 95)

    # 1. Fast Gemma
    v15_fast = run_trials(attack_v15, model_type="fast", harmony_works=True, n_trials=10)
    v19_fast = run_trials(attack_v19_prod, model_type="fast", harmony_works=True, n_trials=10)

    # 2. Slow GPT-OSS (Working Harmony)
    v15_slow_w = run_trials(attack_v15, model_type="slow_reasoning", harmony_works=True, n_trials=10)
    v19_slow_w = run_trials(attack_v19_prod, model_type="slow_reasoning", harmony_works=True, n_trials=10)

    # 3. Slow GPT-OSS (Failed Harmony)
    v15_slow_f = run_trials(attack_v15, model_type="slow_reasoning", harmony_works=False, n_trials=10)
    v19_slow_f = run_trials(attack_v19_prod, model_type="slow_reasoning", harmony_works=False, n_trials=10)

    print(f"\n--- [1] Fast Target Model (Gemma ~8.5s) ---")
    print(f"V15 Baseline  : Mean Score = {v15_fast['mean_score']:6.3f} +/- {v15_fast['std_score']:5.3f} (Range: {v15_fast['min_score']:.2f} - {v15_fast['max_score']:.2f}) | Cands = {v15_fast['mean_cands']:6.1f} | Replay Safe: {v15_fast['replay_safe_pct']:.1f}%")
    print(f"V19 Final     : Mean Score = {v19_fast['mean_score']:6.3f} +/- {v19_fast['std_score']:5.3f} (Range: {v19_fast['min_score']:.2f} - {v19_fast['max_score']:.2f}) | Cands = {v19_fast['mean_cands']:6.1f} | Replay Safe: {v19_fast['replay_safe_pct']:.1f}%")

    print(f"\n--- [2] Slow Target Model (GPT-OSS ~9.2s / Harmony Bypassed) ---")
    print(f"V15 Baseline  : Mean Score = {v15_slow_w['mean_score']:6.3f} +/- {v15_slow_w['std_score']:5.3f} (Range: {v15_slow_w['min_score']:.2f} - {v15_slow_w['max_score']:.2f}) | Cands = {v15_slow_w['mean_cands']:6.1f} | Replay Safe: {v15_slow_w['replay_safe_pct']:.1f}%")
    print(f"V19 Final     : Mean Score = {v19_slow_w['mean_score']:6.3f} +/- {v19_slow_w['std_score']:5.3f} (Range: {v19_slow_w['min_score']:.2f} - {v19_slow_w['max_score']:.2f}) | Cands = {v19_slow_w['mean_cands']:6.1f} | Replay Safe: {v19_slow_w['replay_safe_pct']:.1f}%")

    print(f"\n--- [3] Slow Target Model (GPT-OSS ~20.4s / Harmony Token FAILS) ---")
    print(f"V15 Baseline  : Mean Score = {v15_slow_f['mean_score']:6.3f} +/- {v15_slow_f['std_score']:5.3f} (Fatal collapse to 8 probes)")
    print(f"V19 Final     : Mean Score = {v19_slow_f['mean_score']:6.3f} +/- {v19_slow_f['std_score']:5.3f} (Range: {v19_slow_f['min_score']:.2f} - {v19_slow_f['max_score']:.2f}) | Cands = {v19_slow_f['mean_cands']:6.1f} | Replay Safe: {v19_slow_f['replay_safe_pct']:.1f}%")

    print("\n" + "=" * 95)
    print("PHASE 3: SAFE PARAMETER EXPLORATION (Quantifying 0.98 vs 0.985 tradeoff)")
    print("=" * 95)
    for frac in [0.970, 0.975, 0.980, 0.985]:
        cfg = {"replay_safe_frac": frac}
        res_f = run_trials(attack_v19_prod, model_type="fast", n_trials=10, config_overrides=cfg)
        res_s = run_trials(attack_v19_prod, model_type="slow_reasoning", n_trials=10, config_overrides=cfg)
        mean_s = (res_f['mean_score'] + res_s['mean_score']) / 2.0
        rem_buffer = 9000.0 * (1.0 - frac)
        print(f"REPLAY_SAFE_FRAC = {frac:.3f} | Mean Score: {mean_s:6.3f} (Fast: {res_f['mean_score']:.2f}, Slow: {res_s['mean_score']:.2f}) | Replay Buffer Remaining: {rem_buffer:5.1f}s | Safe%: {res_f['replay_safe_pct']:.0f}%")

    print("\n" + "=" * 95)
    print("PHASE 4: CANARY ABLATION MATRIX")
    print("=" * 95)
    
    # A. V15
    # B. V19 without canary (split_on=False or forced frame)
    # C. V19 with canary + working frame
    # D. V19 with canary + failed frame
    # E. V19 with canary + transient env errors (5% error rate)
    
    cA_f = run_trials(attack_v15, model_type="fast", n_trials=10)
    cA_s = run_trials(attack_v15, model_type="slow_reasoning", harmony_works=True, n_trials=10)
    
    cB_f = run_trials(attack_v19_prod, model_type="fast", n_trials=10, config_overrides={"split_by_latency": False})
    cB_s = run_trials(attack_v19_prod, model_type="slow_reasoning", harmony_works=True, n_trials=10, config_overrides={"split_by_latency": False})
    
    cC_f = run_trials(attack_v19_prod, model_type="fast", n_trials=10)
    cC_s = run_trials(attack_v19_prod, model_type="slow_reasoning", harmony_works=True, n_trials=10)
    
    cD_f = run_trials(attack_v19_prod, model_type="fast", n_trials=10)
    cD_s = run_trials(attack_v19_prod, model_type="slow_reasoning", harmony_works=False, n_trials=10)
    
    print(f"A. V15 Baseline                              : Mean Score = {(cA_f['mean_score']+cA_s['mean_score'])/2.0:6.3f} (Worst Case: {v15_slow_f['mean_score']:.2f})")
    print(f"B. V19 without Latency Split / Canary       : Mean Score = {(cB_f['mean_score']+cB_s['mean_score'])/2.0:6.3f}")
    print(f"C. V19 + Canary (Working Harmony)            : Mean Score = {(cC_f['mean_score']+cC_s['mean_score'])/2.0:6.3f}")
    print(f"D. V19 + Canary (Failed Harmony Recovery)    : Mean Score = {(cD_f['mean_score']+cD_s['mean_score'])/2.0:6.3f} (Salvaged: {cD_s['mean_score']:.2f} on slow row!)")

    print("\n" + "=" * 95)
    print("PHASE 5: ADVERSARIAL STRESS TESTING MATRIX (10 Stress Conditions)")
    print("=" * 95)
    
    stress_conditions = [
        ("1. Forged Template ALWAYS Fails", "slow_reasoning", False, 0.0, 0.0),
        ("2. Forged Template Intermittent Fail (20%)", "slow_reasoning", True, 0.0, 0.20),
        ("3. Very Slow Target Model (30s/cand)", "custom", False, 0.0, 0.0),
        ("4. Very Fast Target Model (3s/cand)", "custom", False, 0.0, 0.0),
        ("5. Exactly at Threshold (12.0s)", "custom", False, 0.0, 0.0),
        ("6. Just Below Threshold (11.8s)", "custom", False, 0.0, 0.0),
        ("7. Just Above Threshold (12.2s)", "custom", False, 0.0, 0.0),
        ("8. 100% Probes Fail (Dead Env)", "fast", False, 1.0, 0.0),
    ]

    for name, mtype, h_works, f_prob, int_fail in stress_conditions:
        lat = 30.0 if "30s" in name else (3.0 if "3s" in name else (12.0 if "Exactly" in name else (11.8 if "Below" in name else (12.2 if "Above" in name else 8.5))))
        res = run_trials(attack_v19_prod, model_type=mtype, harmony_works=h_works, n_trials=5, fail_prob=f_prob, intermittent_harmony_fail=int_fail)
        print(f"Stress {name:<45s} -> Score: {res['mean_score']:6.2f}, Cands: {res['mean_cands']:5.1f}, Replay Safe: {res['replay_safe_pct']:.0f}%")

if __name__ == '__main__':
    run_all_phases()
