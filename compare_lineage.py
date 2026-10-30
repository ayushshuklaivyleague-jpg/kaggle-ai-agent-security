import re
import difflib

files = {
    'V12': 'extracted_v12.py',
    'V15': 'extracted_v15.py',
    'V16': 'extracted_v16.py',
    'V17': 'extracted_v17.py',
    'V18': 'extracted_v18.py',
    'V19': 'extracted_v19.py'
}

data = {}
for name, fpath in files.items():
    with open(fpath, 'r', encoding='utf-8') as f:
        data[name] = f.read()

print("File lengths (chars):")
for k, v in data.items():
    print(f"  {k}: {len(v)} chars, {len(v.splitlines())} lines")

# Check key functions and constants in each
keys = [
    'PAYLOAD', 'TEMPLATE', 'FRAME_TEMPLATE', 'FORGED_TEMPLATE', 'BASE_TEMPLATE',
    'MARGIN_S', 'SLOWEST0', 'SLOWEST_MULT', 'MARGIN_FLOOR_MIN', 'MARGIN_SLOWEST_COEF',
    'FILL_BUDGET_FRAC', 'HARD_N_CAP', 'SPLIT_BY_LATENCY', 'SPLIT_THRESHOLD_S',
    'SPLIT_CLASSIFY_N', 'BURST_K', 'REPLAY_SAFE_SIZING', 'REPLAY_SAFE_FRAC',
    'PROBE_HOPS', 'REPLAY_COST_COEF', 'SLOW_MULTIPOST_N', 'REPLAY_BUDGET_MULT',
    'FALLBACK_N', 'WARMUP_IDX', 'DEFAULT_BUDGET_S', 'verify_forged_pending',
    'ENABLE_SCOUTING', 'ENABLE_BEHAVIORAL_ARCHIVE', 'Wilson', 'StrategyGenerator'
]

print("\nSymbol / Constant Presence:")
for k in keys:
    presence = [name for name, content in data.items() if k in content]
    print(f"  {k:25s}: {', '.join(presence)}")
