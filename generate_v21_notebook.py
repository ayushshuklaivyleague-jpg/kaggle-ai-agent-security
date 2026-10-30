import json

with open("attack_v21_experimental.py", "r", encoding="utf-8") as f:
    attack_code_content = f.read()

notebook_content = {
    "cells": [
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import sys, glob\n",
                "from pathlib import Path\n",
                "sys.argv = [sys.argv[0]]\n",
                "for candidate in glob.glob('/kaggle/input/**/kaggle_evaluation', recursive=True):\n",
                "    root = str(Path(candidate).parent)\n",
                "    if root not in sys.path:\n",
                "        sys.path.insert(0, root)\n",
                "    print('Dataset root:', root)\n",
                "    break\n",
                "print('Setup complete')\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "attack_code = r'''" + attack_code_content + "'''\n",
                "\n",
                "import os\n",
                "os.makedirs('/kaggle/working', exist_ok=True)\n",
                "with open('/kaggle/working/attack.py', 'w', encoding='utf-8') as f:\n",
                "    f.write(attack_code)\n",
                "print('attack.py written, chars:', len(attack_code))\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os, csv\n",
                "if os.getenv('KAGGLE_IS_COMPETITION_RERUN'):\n",
                "    import kaggle_evaluation.jed_attack_134815.jed_attack_inference_server as server\n",
                "    server.JEDAttackInferenceServer().serve()\n",
                "else:\n",
                "    with open('/kaggle/working/submission.csv', 'w', newline='') as fh:\n",
                "        w = csv.writer(fh); w.writerow(['Id', 'Score'])\n",
                "        w.writerows([['gpt_oss_public', 0.0], ['gpt_oss_private', 0.0], ['gemma_public', 0.0], ['gemma_private', 0.0]])\n",
                "    print('placeholder submission.csv written. Set GPU T4 x2, Internet Off, then Submit.')\n"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.12.13"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 2
}

with open("ai-v21-experimental.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook_content, f, indent=1)

print("Generated ai-v21-experimental.ipynb successfully.")
