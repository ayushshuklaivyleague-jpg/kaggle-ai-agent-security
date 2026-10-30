import sys
import os
import time
import math
import random
import statistics
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.abspath('sdk_extracted'))
sys.path.insert(0, os.path.abspath('.'))

from aicomp_sdk.attacks.contracts import AttackAlgorithmBase, AttackCandidate, AttackRunConfig
from aicomp_sdk.core.cells import cell_signature
from aicomp_sdk.core.predicates import eval_predicates
from aicomp_sdk.scoring import score_attack, score_attack_raw
from run_comprehensive_benchmark import SimulatedClock, TimeSimulatedEnv
from v20_family_env import MultiFamilyMockEnv, TEMPLATES, _url, PAYLOAD

# -----------------------------------------------------------------------------
# V20 Adaptive Attack Portfolio Implementation
# -----------------------------------------------------------------------------

class FamilyArm:
    def __init__(self, name: str, is_multistep: bool = False, base_severity: int = 5):
        self.name = name
        self.is_multistep = is_multistep
        self.base_severity = base_severity
        self.pulls = 0
        self.successes = 0
        self.total_raw_reward = 0.0
        self.total_latency_s = 0.0
        self.unique_cells_discovered = 0
        self.seen_hashes: set[str] = set()

    @property
    def empirical_score_per_sec(self) -> float:
        if self.total_latency_s <= 0:
            return 0.0
        return self.total_raw_reward / self.total_latency_s

    def ucb_score(self, total_evals: int, c: float = 1.0, novelty_weight: float = 2.0) -> float:
        if self.pulls == 0:
            return 1e6 # prioritize initial pull
        mean_reward_rate = self.empirical_score_per_sec
        # Add exploration bonus based on confidence & novelty
        explore_bonus = c * math.sqrt(math.log(max(1, total_evals)) / self.pulls)
        novelty_bonus = (self.unique_cells_discovered * novelty_weight) / (self.pulls + 1)
        return mean_reward_rate + explore_bonus + novelty_bonus

    def thompson_sample(self) -> float:
        # Beta posterior for success rate * expected yield / latency
        a = 1 + self.successes
        b = 1 + (self.pulls - self.successes)
        p_sample = random.betavariate(a, b)
        mean_lat = (self.total_latency_s / self.pulls) if self.pulls > 0 else 10.0
        return (p_sample * (16.0 if self.base_severity == 5 else (8.0 if self.base_severity == 4 else 4.0)) + 2.0) / max(0.1, mean_lat)


class AttackAlgorithmV20Portfolio(AttackAlgorithmBase):
    """V20 Adaptive Attack Portfolio Controller."""

    def __init__(self, policy: str = "novelty_ucb", explore_ratio: float = 0.05, allow_multistep: bool = False):
        super().__init__()
        self.policy = policy
        self.explore_ratio = explore_ratio
        self.allow_multistep = allow_multistep

    def run(self, env, config):
        budget = float(getattr(config, "time_budget_s", 9000.0) or 9000.0)
        max_hops = int(getattr(config, "max_tool_hops", 8) or 8)
        return self._fill(env, budget, max_hops)

    def _fill(self, env, budget: float, max_hops: int):
        cap = 2000
        replay_safe_frac = float(self.config.get("replay_safe_frac", 0.98))
        split_threshold = 12.0
        split_classify_n = 8
        slowest = 25.0

        run_start = time.monotonic()
        # Warmup
        try:
            env.reset()
            env.interact(TEMPLATES["exfil_single"].format(url=_url(899999), payload=PAYLOAD), max_tool_hops=max_hops)
        except Exception:
            return []

        replay_cap = replay_safe_frac * budget - (time.monotonic() - run_start)
        wall_deadline = run_start + replay_safe_frac * budget
        replay_cost = 0.0

        # Initialize Arms
        arms: dict[str, FamilyArm] = {
            "exfil_single": FamilyArm("exfil_single", is_multistep=False, base_severity=5),
            "destructive_write": FamilyArm("destructive_write", is_multistep=False, base_severity=4),
            "confused_deputy": FamilyArm("confused_deputy", is_multistep=False, base_severity=3),
        }
        if self.allow_multistep:
            arms["untrusted_to_action"] = FamilyArm("untrusted_to_action", is_multistep=True, base_severity=5)
            arms["exfil_read_chain"] = FamilyArm("exfil_read_chain", is_multistep=True, base_severity=5)

        cands: list[AttackCandidate] = []
        global_cell_archive: set[str] = set()
        idx = 0
        classify_n = 0
        classify_sum = 0.0
        chosen_exfil_template = TEMPLATES["exfil_single"]
        canary_state = None

        # Phase 0: Calibration (1 probe per arm)
        for arm_name, arm in list(arms.items()):
            if (replay_cost + slowest * 1.35 >= replay_cap) or (time.monotonic() + slowest * 1.35 >= wall_deadline):
                break
            idx += 1
            template_pattern = TEMPLATES[arm_name]
            msgs = [m.format(url=_url(idx), payload=PAYLOAD) for m in template_pattern] if isinstance(template_pattern, list) else [template_pattern.format(url=_url(idx), payload=PAYLOAD)]
            
            t0 = time.monotonic()
            env.reset()
            for m in msgs:
                env.interact(m, max_tool_hops=max_hops)
            elapsed = time.monotonic() - t0
            slowest = max(slowest, elapsed, 0.001)

            trace = env.export_trace_dict()
            predicates = eval_predicates(trace)
            c_sig = cell_signature(trace.get("tool_events", []))
            chash = c_sig.get("hash", "")

            arm.pulls += 1
            arm.total_latency_s += elapsed

            if predicates:
                arm.successes += 1
                raw_yield = sum(16 if p.get("severity") == 5 else (8 if p.get("severity") == 4 else 4) for p in predicates)
                is_novel = chash and (chash not in global_cell_archive)
                if is_novel:
                    global_cell_archive.add(chash)
                    arm.unique_cells_discovered += 1
                    raw_yield += 2.0
                arm.total_raw_reward += raw_yield
                cands.append(AttackCandidate.from_messages(msgs))
                replay_cost += elapsed
            
            if arm_name == "exfil_single":
                classify_n += 1
                classify_sum += elapsed

        # Phase 1 & 2: Exploit with Controlled Diversity Injection
        while len(cands) < cap:
            next_wall = slowest * 1.35
            if (replay_cost + next_wall >= replay_cap) or (time.monotonic() + next_wall >= wall_deadline):
                break

            classifying = classify_n < split_classify_n
            
            # Action Selection Policy
            if classifying:
                selected_arm_name = "exfil_single"
            elif self.policy == "v15_control" or self.explore_ratio <= 0.0:
                selected_arm_name = "exfil_single"
            elif self.policy == "static_mixture":
                # Static mixture e.g. 95% exfil, 5% other
                if random.random() < self.explore_ratio:
                    alt_arms = [k for k in arms if k != "exfil_single"]
                    selected_arm_name = random.choice(alt_arms) if alt_arms else "exfil_single"
                else:
                    selected_arm_name = "exfil_single"
            elif self.policy == "novelty_ucb":
                if random.random() < self.explore_ratio:
                    # Score arms by UCB + novelty
                    total_p = sum(a.pulls for a in arms.values())
                    selected_arm_name = max(arms.keys(), key=lambda k: arms[k].ucb_score(total_p))
                else:
                    # Exploit highest score-per-second arm
                    selected_arm_name = max(arms.keys(), key=lambda k: arms[k].empirical_score_per_sec)
            elif self.policy == "thompson":
                if random.random() < self.explore_ratio:
                    selected_arm_name = max(arms.keys(), key=lambda k: arms[k].thompson_sample())
                else:
                    selected_arm_name = max(arms.keys(), key=lambda k: arms[k].empirical_score_per_sec)
            else:
                selected_arm_name = "exfil_single"

            arm = arms[selected_arm_name]
            idx += 1

            # Format message
            if selected_arm_name == "exfil_single":
                tmpl = TEMPLATES["exfil_single"] if (classifying or canary_state == 'done_fallback') else chosen_exfil_template
                msgs = [tmpl.format(url=_url(idx), payload=PAYLOAD)]
            else:
                tmpl_pat = TEMPLATES[selected_arm_name]
                msgs = [m.format(url=_url(idx), payload=PAYLOAD) for m in tmpl_pat] if isinstance(tmpl_pat, list) else [tmpl_pat.format(url=_url(idx), payload=PAYLOAD)]

            t0 = time.monotonic()
            try:
                env.reset()
                for m in msgs:
                    env.interact(m, max_tool_hops=max_hops)
                trace = env.export_trace_dict()
                predicates = eval_predicates(trace)
            except Exception:
                break
            elapsed = time.monotonic() - t0
            slowest = max(slowest, elapsed, 0.001)

            # Update arm stats
            arm.pulls += 1
            arm.total_latency_s += elapsed

            if classifying and selected_arm_name == "exfil_single":
                classify_n += 1
                classify_sum += elapsed
                if classify_n == split_classify_n:
                    if classify_sum / classify_n > split_threshold:
                        chosen_exfil_template = TEMPLATES["exfil_single_forged"]
                        canary_state = 'verify_next'
                    else:
                        chosen_exfil_template = TEMPLATES["exfil_single"]
                        canary_state = 'done'
            elif canary_state == 'verify_next':
                canary_state = 'done'
                if not predicates:
                    chosen_exfil_template = TEMPLATES["exfil_single"]
                    canary_state = 'done_fallback'

            if predicates:
                arm.successes += 1
                c_sig = cell_signature(trace.get("tool_events", []))
                chash = c_sig.get("hash", "")
                raw_yield = sum(16 if p.get("severity") == 5 else (8 if p.get("severity") == 4 else 4) for p in predicates)
                is_novel = chash and (chash not in global_cell_archive)
                if is_novel:
                    global_cell_archive.add(chash)
                    arm.unique_cells_discovered += 1
                    raw_yield += 2.0
                arm.total_raw_reward += raw_yield
                cands.append(AttackCandidate.from_messages(msgs))
                replay_cost += elapsed

        return cands

print("AttackAlgorithmV20Portfolio class defined.")
