import json
import re
import os

def extract_code(nb_path, out_py):
    if not os.path.exists(nb_path):
        print(f"Skipping missing {nb_path}")
        return
    with open(nb_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for i, c in enumerate(data.get('cells', [])):
        src = ''.join(c.get('source', []))
        if 'attack_code' in src:
            # find raw string inside attack_code = r'''...''' or similar
            m = re.search(r"attack_code\s*=\s*r?('''|\"\"\")(.*?)\1", src, re.DOTALL)
            if m:
                with open(out_py, 'w', encoding='utf-8') as out:
                    out.write(m.group(2))
                print(f"Wrote {out_py} from {nb_path} cell {i} ({len(m.group(2))} chars)")
                return
            else:
                with open(out_py, 'w', encoding='utf-8') as out:
                    out.write(src)
                print(f"Wrote {out_py} raw from {nb_path} cell {i} ({len(src)} chars)")
                return
        elif 'class AttackAlgorithm' in src:
            with open(out_py, 'w', encoding='utf-8') as out:
                out.write(src)
            print(f"Wrote {out_py} directly from {nb_path} cell {i} ({len(src)} chars)")
            return

extract_code('ai-v3.ipynb', 'extracted_v3.py')
extract_code('ai-agent-security-v12.ipynb', 'extracted_v12.py')
extract_code('ai-agent-security-v15.ipynb', 'extracted_v15.py')
extract_code('ai-v16.ipynb', 'extracted_v16.py')
extract_code('ai-v17.ipynb', 'extracted_v17.py')
extract_code('ai-v18.ipynb', 'extracted_v18.py')
extract_code('ai-agent-security-v19.ipynb', 'extracted_v19.py')
