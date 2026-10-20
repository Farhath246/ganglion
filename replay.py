"""
Replay - offline consolidation, the sleep-adjacent piece.

Sleep is thought to be when the brain replays and consolidates recent
experience. This re-feeds a sample of past outcomes (logged to
Memory.history by Brain every time a candidate is rewarded) back into
basal_ganglia's learning - genuine experience replay, a real
reinforcement-learning technique, not only a biological metaphor.
"""

import random


class ReplayConsolidator:
    def __init__(self, sample_size: int = 5):
        self.sample_size = sample_size

    def run(self, memory, basal_ganglia) -> int:
        """Replay a sample of past candidate outcomes back into
        basal_ganglia. Returns how many were replayed; 0 if there's
        nothing logged yet to replay."""
        if basal_ganglia is None:
            return 0
        outcomes = [h for h in memory.history if h.get("key") == "_replay_outcome"]
        if not outcomes:
            return 0
        sample = random.sample(outcomes, min(self.sample_size, len(outcomes)))
        for entry in sample:
            value = entry["value"]
            basal_ganglia.reward(value["name"], value["success"])
        return len(sample)
