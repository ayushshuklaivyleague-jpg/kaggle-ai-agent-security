import difflib

def show_diff(f1, f2, n1, n2):
    with open(f1, 'r', encoding='utf-8') as a, open(f2, 'r', encoding='utf-8') as b:
        lines1 = a.readlines()
        lines2 = b.readlines()
    diff = list(difflib.unified_diff(lines1, lines2, fromfile=n1, tofile=n2, n=3))
    print(f"=== DIFF {n1} vs {n2} ({len(diff)} diff lines) ===")
    print("".join(diff[:60]))
    if len(diff) > 60:
        print(f"... and {len(diff)-60} more diff lines")

show_diff('extracted_v15.py', 'extracted_v19.py', 'V15', 'V19')
show_diff('extracted_v12.py', 'extracted_v15.py', 'V12', 'V15')
