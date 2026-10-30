"""Ultimate Mathematical Score Target Backsolver: 120 to 155+ (V25 Directive).

Grounded in measured empirical trace densities, compliance distributions,
and replay packing constraints.
"""

from __future__ import annotations

def run_ultimate_score_backsolver():
    print("=" * 125)
    print("ULTIMATE MATHEMATICAL SCORE TARGET BACKSOLVER: 120.0 TO 155.0+")
    print("=" * 125)

    targets = [120.0, 125.0, 130.0, 135.0, 140.0, 145.0, 147.530, 150.0, 155.0]
    budget_s = 9000.0 * 0.982  # 8838s effective replay budget

    print(
        f"{'Target':<8s} | {'Req Raw':<9s} | {'Req Pts/s':<10s} | {'K=4 Cands':<10s} | {'K=6 Cands':<10s} | {'K=8 Cands':<10s} | {'Req Lat/Cand(K=8)':<18s} | {'Feasibility Condition'}"
    )
    print("-" * 125)

    # Point yields per candidate with unique cell bonus (+2.0):
    # K=4: 4 * 16 + 2 = 66 raw pts
    # K=6: 6 * 16 + 2 = 98 raw pts
    # K=8: 8 * 16 + 2 = 130 raw pts

    for target in targets:
        req_raw = target * 200.0
        req_pts_per_sec = req_raw / budget_s

        k4_cands = req_raw / 66.0
        k6_cands = req_raw / 98.0
        k8_cands = req_raw / 130.0

        req_lat_k8 = budget_s / k8_cands

        if req_pts_per_sec <= 2.80:
            feasibility = "Achieved (V24 Mean = 120.63)"
        elif req_pts_per_sec <= 3.00:
            feasibility = "Achieved (Gemma Fast Model = 132.22)"
        elif req_pts_per_sec <= 3.15:
            feasibility = "Sustained K=6 (Structured Numbered Prompt)"
        elif req_pts_per_sec <= 3.30:
            feasibility = "High K=6..8 Mixed Burst Density"
        elif req_pts_per_sec <= 3.35:
            feasibility = "Near-Full 8-Hop Saturation (147.530 Benchmark)"
        elif req_pts_per_sec <= 3.42:
            feasibility = "Full 8-Hop Saturation + Zero-Waste Replay Packing (150+)"
        else:
            feasibility = "Theoretical Max (Requires Sub-35s K=8 Latency on All Models)"

        print(
            f"{target:<8.3f} | {req_raw:<9.1f} | {req_pts_per_sec:<10.3f} | {k4_cands:<10.1f} | {k6_cands:<10.1f} | {k8_cands:<10.1f} | {req_lat_k8:<18.2f}s | {feasibility}"
        )

    print("\n[KEY INSIGHTS]")
    print("1. Target 147.530 requires exactly 227 candidates at full K=8 (130 pts/cand) with avg latency <= 38.9s.")
    print("2. Target 150.000 requires exactly 231 candidates at full K=8 (130 pts/cand) with avg latency <= 38.2s.")
    print("3. If model compliance drops to K=6 (98 pts/cand), reaching 150 requires 306 candidates with latency <= 28.8s.")
    print("4. Therefore, prompt engineering for 8-hop continuation (Format E) is mathematically mandatory to reach 150+.")


if __name__ == "__main__":
    run_ultimate_score_backsolver()
