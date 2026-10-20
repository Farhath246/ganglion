"""
Hebbian association - "fire together, wire together."

Basal ganglia tracks a candidate's overall win rate, context-free. Real
synaptic learning is contextual: a pathway strengthens specifically
between the input that was active and the output that followed. This
tracks (context, candidate) pairs instead of just candidates, so a
candidate that works well in one situation and poorly in another gets
scored differently depending on what's currently going on - via plain
co-occurrence counting, not anything resembling real synaptic
plasticity.
"""

import json
import os


class HebbianAssociator:
    def __init__(self, path: str = "hebbian.json"):
        self.path = path
        self.weights = {}  # "context|candidate" -> {"wins": int, "attempts": int}
        self._load()

    @staticmethod
    def context_key(world_model) -> str:
        """A coarse context signature: whether hazards are present, and
        how many known elements there are, bucketed. Swap this for
        something richer if finer-grained context matters."""
        hazard_flag = "hazard" if world_model.hazards else "clear"
        element_bucket = min(len(world_model.known_elements), 5)
        return f"{hazard_flag}:{element_bucket}"

    def bias(self, context: str, candidate_name: str) -> float:
        s = self.weights.get(f"{context}|{candidate_name}")
        if not s or s["attempts"] == 0:
            return 0.0  # no association learned yet - neutral
        return (s["wins"] / s["attempts"]) - 0.5  # -0.5..+0.5, centered on "no preference"

    def update(self, context: str, candidate_name: str, success: bool):
        key = f"{context}|{candidate_name}"
        s = self.weights.setdefault(key, {"wins": 0, "attempts": 0})
        s["attempts"] += 1
        if success:
            s["wins"] += 1
        self._save()

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.weights, f, indent=2)

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path) as f:
                self.weights = json.load(f)
