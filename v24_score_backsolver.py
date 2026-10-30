import math

def solve_v24_score_targets():
    print("=" * 115)
    print("V24 MATHEMATICAL SCORE TARGET BACKSOLVER: 100 TO 150+")
    print("=" * 115)

    targets = [100.0, 110.0, 120.0, 125.0, 130.0, 135.0, 140.0, 145.0, 147.530, 150.0]
    budget_s = 9000.0 * 0.980 # 8820s effective replay budget

    print(f"{'Target Score':<14s} | {'Req Raw Score':<14s} | {'Req Pts/sec':<14s} | {'K=2 Cands':<12s} | {'K=4 Cands':<12s} | {'K=6 Cands':<12s} | {'Feasibility'}")
    print("-" * 115)

    for target in targets:
        req_raw = target * 200.0
        req_pts_per_sec = req_raw / budget_s

        k2_cands = req_raw / 34.0
        k4_cands = req_raw / 66.0
        k6_cands = req_raw / 98.0

        feasibility = "Achieved (V24-BALANCED)" if req_pts_per_sec <= 2.80 else (
            "Achieved on Gemma Fast Row" if req_pts_per_sec <= 3.05 else (
                "Requires Sustained K=5..6 Burst" if req_pts_per_sec <= 3.25 else "Requires Max K=8 Hop Saturation"
            )
        )

        print(f"{target:<14.3f} | {req_raw:<14.1f} | {req_pts_per_sec:<14.3f} | {k2_cands:<12.1f} | {k4_cands:<12.1f} | {k6_cands:<12.1f} | {feasibility}")

if __name__ == '__main__':
    solve_v24_score_targets()
