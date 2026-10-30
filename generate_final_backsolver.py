"""Phase 12: Final Mathematical Backsolver for Targets 125 -> 155."""

import csv
import math

BUDGET_S = 8838.0  # Effective replay budget after 0.982 governor margin

targets = [125.0, 130.0, 135.0, 140.0, 145.0, 147.530, 150.0, 155.0]
rows = []

for t in targets:
    req_raw = (t / 1000.0) * 200000.0
    req_density = req_raw / BUDGET_S

    # Scenario A: 7-Hop Saturated Burst (Mean latency 32.5s)
    lat_a = 32.5
    cands_a = math.floor(BUDGET_S / lat_a)
    req_raw_per_cand_a = req_raw / cands_a
    # raw_yield = 16.0 * hops + 2.0 * 1
    req_hops_a = max(1.0, (req_raw_per_cand_a - 2.0) / 16.0)

    # Scenario B: 8-Hop High-Burst (Mean latency 36.0s)
    lat_b = 36.0
    cands_b = math.floor(BUDGET_S / lat_b)
    req_raw_per_cand_b = req_raw / cands_b
    req_hops_b = max(1.0, (req_raw_per_cand_b - 2.0) / 16.0)

    # Scenario C: 6-Hop Fast Burst (Mean latency 28.5s)
    lat_c = 28.5
    cands_c = math.floor(BUDGET_S / lat_c)
    req_raw_per_cand_c = req_raw / cands_c
    req_hops_c = max(1.0, (req_raw_per_cand_c - 2.0) / 16.0)

    rows.append({
        "Target_Score": t,
        "Required_Raw_Score": int(round(req_raw)),
        "Required_Pts_Per_Sec": round(req_density, 3),
        "K7_Required_Hops_Per_Trace": round(req_hops_a, 2),
        "K7_Candidates_Packed": cands_a,
        "K8_Required_Hops_Per_Trace": round(req_hops_b, 2),
        "K8_Candidates_Packed": cands_b,
        "K6_Required_Hops_Per_Trace": round(req_hops_c, 2),
        "K6_Candidates_Packed": cands_c,
    })

with open("final_backsolver.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print("[OK] Exported final_backsolver.csv")
