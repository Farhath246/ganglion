"""
Memory - episodic history, consolidated into semantic facts.

Two stores. `history` is the episode log: every key/value the system
wrote, in order, which is what replay reads from. `semantic` holds the
few things that proved themselves by repeating, promoted by
`consolidate()`. Repeats are what turn an episode into a fact.

Deliberately not a brain: a human's consolidation is re-consolidation
with interference and time-decay; here it is a count and a threshold.
"""

import json
import os
import time


class Memory:
    def __init__(self, path: str = "mem.json"):
        self.path = path
        self.history = []
        self.semantic = {}
        self.recall_stats = {}
        self._load()

    def remember(self, key: str, value):
        self.history.append({"ts": time.time(), "key": key, "value": value})

    def recall(self, key: str):
        stats = self.recall_stats.setdefault(key, {"count": 0})
        stats["count"] += 1
        for entry in reversed(self.history):
            if entry["key"] == key:
                return entry["value"]
        return None

    def consolidate(self, min_repeats: int = 3) -> dict:
        """Promote keys seen at least `min_repeats` times into the
        semantic store. Returns what was promoted."""
        counts = {}
        for entry in self.history:
            counts[entry["key"]] = counts.get(entry["key"], 0) + 1
        promoted = {}
        for key, seen in counts.items():
            if seen < min_repeats or key in self.semantic:
                continue
            value = self._latest_value(key)
            self.semantic[key] = value
            promoted[key] = value
        return promoted

    def _latest_value(self, key: str):
        for entry in reversed(self.history):
            if entry["key"] == key:
                return entry["value"]
        return None

    def save(self):
        with open(self.path, "w") as fh:
            json.dump({"semantic": self.semantic, "history": self.history}, fh, default=str)

    def _load(self):
        if not os.path.exists(self.path):
            return
        with open(self.path) as fh:
            data = json.load(fh)
        self.semantic = data.get("semantic", {})
        self.history = data.get("history", [])
