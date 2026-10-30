import sys
import os
import time

sys.path.insert(0, os.path.abspath('sdk_extracted'))
sys.path.insert(0, os.path.abspath('.'))

from aicomp_sdk.core.predicates import eval_predicates
from aicomp_sdk.core.cells import cell_signature
from aicomp_sdk.scoring import score_attack, score_attack_raw

def analyze_burst_score_density():
    print("=" * 90)
    print("PHASE 2 & 6: SCORE DENSITY ANALYSIS FOR BURST K (1 TO 8)")
    print("=" * 90)

    # Assume latency model based on per-hop cost:
    # Single hop overhead = T_base + K * T_hop
    # On Gemma: T_base ~ 4.0s, T_hop ~ 4.5s (K=1 -> 8.5s, K=2 -> 13.0s, K=4 -> 22.0s)
    # On GPT-OSS (Forged): T_base ~ 3.5s, T_hop ~ 5.5s (K=1 -> 9.0s, K=2 -> 14.5s, K=4 -> 25.5s)

    gemma_base, gemma_hop = 4.0, 4.5
    gpt_base, gpt_hop = 3.5, 5.5

    print(f"{'Burst K':<8s} | {'Raw Score':<10s} | {'Gemma Lat(s)':<13s} | {'Gemma Score/s':<14s} | {'GPT Lat(s)':<11s} | {'GPT Score/s':<13s} | {'Normalized Yield'}")
    print("-" * 90)

    for k in range(1, 9):
        # 1 candidate with K successful exfil posts
        events = [
            {"name": "http.post", "ok": True, "side_effect": "SHARE", "scope": "EXT", "source": "agent", "args": {"url": f"http://node_{i}.co", "data": "SECRET_MARKER"}}
            for i in range(k)
        ]
        trace = {"seed": 42, "user_messages": ["burst test"], "tool_events": events}
        preds = eval_predicates(trace)
        sig = cell_signature(events)
        findings = [{"score_cell_signature": sig, "predicates": preds}]
        raw = score_attack_raw(findings)
        norm = score_attack(findings, normalize=True)

        gemma_lat = gemma_base + k * gemma_hop
        gemma_density = raw / gemma_lat

        gpt_lat = gpt_base + k * gpt_hop
        gpt_density = raw / gpt_lat

        print(f"{k:<8d} | {raw:<10.1f} | {gemma_lat:<13.1f} | {gemma_density:<14.3f} | {gpt_lat:<11.1f} | {gpt_density:<13.3f} | {norm:<16.4f}")

if __name__ == '__main__':
    analyze_burst_score_density()
