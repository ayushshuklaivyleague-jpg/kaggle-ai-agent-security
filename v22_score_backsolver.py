import math

def solve_score_targets():
    print("=" * 105)
    print("V22 MATHEMATICAL SCORE TARGET BACKSOLVER (90 TO 147.530)")
    print("=" * 105)

    targets = [90.0, 100.0, 110.0, 120.0, 130.0, 140.0, 147.530]
    budget_s = 9000.0 * 0.980 # 8820s effective replay budget

    print(f"{'Target Score':<14s} | {'Req Raw Score':<14s} | {'Req Raw Pts/sec':<16s} | {'K=1 Cands Req':<15s} | {'K=2 Cands Req':<15s} | {'K=4 Cands Req':<15s} | {'Feasibility'}")
    print("-" * 105)

    for target in targets:
        # target = (raw_score / 200,000) * 1000 => raw_score = target * 200
        req_raw = target * 200.0
        req_pts_per_sec = req_raw / budget_s

        # At K=1: 18 raw/cand
        k1_cands = req_raw / 18.0
        # At K=2: 34 raw/cand
        k2_cands = req_raw / 34.0
        # At K=4: 66 raw/cand
        k4_cands = req_raw / 66.0

        feasibility = "Plausible (K=1)" if req_pts_per_sec <= 2.15 else (
            "Requires K>=2 Burst" if req_pts_per_sec <= 2.65 else (
                "Requires K>=4 Burst" if req_pts_per_sec <= 3.05 else "Requires K>=8 Saturation"
            )
        )

        print(f"{target:<14.3f} | {req_raw:<14.1f} | {req_pts_per_sec:<16.3f} | {k1_cands:<15.1f} | {k2_cands:<15.1f} | {k4_cands:<15.1f} | {feasibility}")

if __name__ == '__main__':
    solve_score_targets()
