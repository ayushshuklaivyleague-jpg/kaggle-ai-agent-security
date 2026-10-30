import sys
import os
import time

sys.path.insert(0, os.path.abspath('sdk_extracted'))
sys.path.insert(0, os.path.abspath('.'))

from test_fixed_canary import AttackAlgorithmFixedV19, fixed_module
from run_comprehensive_benchmark import run_attack_simulated

def run_param_sweeps():
    print("=" * 90)
    print("FOURTH: CONTROLLED PARAMETER SWEEPS ON FIXED V19")
    print("=" * 90)

    # 1. REPLAY_SAFE_FRAC Sweep
    print("\n[1] REPLAY_SAFE_FRAC Sweep (Testing 0.95 to 0.985):")
    print(f"{'Config':<24s} | {'Fast Cands':<10s} | {'Slow Cands':<10s} | {'Mean Score':<10s} | {'Replay Headroom':<15s} | {'Safety vs V15'}")
    print("-" * 90)
    for frac in [0.95, 0.96, 0.97, 0.975, 0.98, 0.985]:
        cfg = {"replay_safe_frac": frac}
        r_f = run_attack_simulated(fixed_module, model_type="fast", harmony_works=True, config_overrides=cfg)
        r_s = run_attack_simulated(fixed_module, model_type="slow_reasoning", harmony_works=True, config_overrides=cfg)
        mean_sc = (r_f['score'] + r_s['score']) / 2.0
        headroom = 9000.0 * (1.0 - frac)
        safety = "Identical" if frac == 0.98 else ("Safer" if frac < 0.98 else "Riskier")
        print(f"REPLAY_SAFE_FRAC={frac:<6.3f} | {r_f['total_candidates']:<10d} | {r_s['total_candidates']:<10d} | {mean_sc:<10.3f} | {headroom:<12.1f}s | {safety}")

    # 2. MARGIN_S Sweep (when adaptive margin is active / replay_safe_sizing=False or as cushion)
    print("\n[2] MARGIN_S Sweep (with replay_safe_sizing=False fallback):")
    print(f"{'Config':<24s} | {'Fast Cands':<10s} | {'Slow Cands':<10s} | {'Mean Score':<10s} | {'Safety vs V15'}")
    print("-" * 75)
    for margin in [37.0, 42.0, 47.0, 50.0, 55.0]:
        cfg = {"replay_safe_sizing": False, "margin_s": margin}
        r_f = run_attack_simulated(fixed_module, model_type="fast", harmony_works=True, config_overrides=cfg)
        r_s = run_attack_simulated(fixed_module, model_type="slow_reasoning", harmony_works=True, config_overrides=cfg)
        mean_sc = (r_f['score'] + r_s['score']) / 2.0
        safety = "Riskier" if margin < 47.0 else ("Identical" if margin == 47.0 else "Safer")
        print(f"MARGIN_S={margin:<6.1f}s        | {r_f['total_candidates']:<10d} | {r_s['total_candidates']:<10d} | {mean_sc:<10.3f} | {safety}")

    # 3. SPLIT_THRESHOLD_S Sweep
    print("\n[3] SPLIT_THRESHOLD_S Sweep (Threshold between Fast ~8.5s and Slow ~20.4s):")
    print(f"{'Config':<24s} | {'Gemma Classified':<18s} | {'GPT-OSS Classified':<18s} | {'Separation Margin'}")
    print("-" * 80)
    for thresh in [8.0, 10.0, 12.0, 14.0, 16.0, 18.0]:
        # Fast gemma ~8.5s, Slow gpt_oss ~20.4s
        gemma_cls = "SLOW (ERROR)" if 8.5 > thresh else "FAST (CORRECT)"
        gpt_cls = "SLOW (CORRECT)" if 20.4 > thresh else "FAST (ERROR)"
        sep = f"+{thresh-8.5:.1f}s / -{20.4-thresh:.1f}s"
        print(f"SPLIT_THRESHOLD={thresh:<5.1f}s    | {gemma_cls:<18s} | {gpt_cls:<18s} | {sep}")

    # 4. SLOWEST_MULT Sweep
    print("\n[4] SLOWEST_MULT Sweep (Next-candidate latency buffer multiplier):")
    print(f"{'Config':<24s} | {'Fast Cands':<10s} | {'Slow Cands':<10s} | {'Mean Score':<10s} | {'Safety vs V15'}")
    print("-" * 75)
    for mult in [1.10, 1.20, 1.35, 1.50, 1.75]:
        cfg = {"slowest_mult": mult}
        r_f = run_attack_simulated(fixed_module, model_type="fast", harmony_works=True, config_overrides=cfg)
        r_s = run_attack_simulated(fixed_module, model_type="slow_reasoning", harmony_works=True, config_overrides=cfg)
        mean_sc = (r_f['score'] + r_s['score']) / 2.0
        safety = "Riskier" if mult < 1.35 else ("Identical" if mult == 1.35 else "Safer")
        print(f"SLOWEST_MULT={mult:<6.2f}    | {r_f['total_candidates']:<10d} | {r_s['total_candidates']:<10d} | {mean_sc:<10.3f} | {safety}")

    # 5. MARGIN_SLOWEST_COEF Sweep
    print("\n[5] MARGIN_SLOWEST_COEF Sweep (Adaptive margin ramp rate):")
    print(f"{'Config':<24s} | {'Adaptive Floor (Fast)':<22s} | {'Adaptive Floor (Slow)':<22s}")
    print("-" * 75)
    for coef in [1.5, 2.0, 2.5, 3.0, 3.5]:
        fast_fl = min(47.0, 4.0 + 8.5 * coef)
        slow_fl = min(47.0, 4.0 + 20.4 * coef)
        print(f"SLOWEST_COEF={coef:<5.1f}    | {fast_fl:<22.1f}s | {slow_fl:<22.1f}s (Capped at 47.0s)")

    # 6. PROBE_HOPS & REPLAY_COST_COEF Sweep
    print("\n[6] PROBE_HOPS & REPLAY_COST_COEF Sweep:")
    print("PROBE_HOPS=0 (default 8 hops, coef=1.0) is proven 100% matched with Kaggle evaluator gateway.")
    print("PROBE_HOPS=1 requires accurate REPLAY_COST_COEF estimation (~1.5-2.0x). If uncalibrated, risks replay timeout.")

if __name__ == '__main__':
    run_param_sweeps()
