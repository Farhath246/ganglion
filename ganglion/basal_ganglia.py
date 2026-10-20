"""
Basal ganglia - arbitration between candidate actions.

The basal ganglia pick between competing candidates and learn from the
outcome: a candidate that works gets picked more, one that fails gets
picked less. Two rules do the work here. A candidate that has never
been tried gets a fair trial first - otherwise a bad candidate could
never be ruled out and a good one might never be confirmed. After
that, the highest win rate wins, with a configurable exploration rate
for the occasional gamble.
"""

import json
import os
import random


class Candidate:
    def __init__(self, name: str, plan: list):
        self.name = name
        self.plan = plan


class BasalGanglia:
    def __init__(self, path: str = "basal_ganglia.json", exploration: float = 0.0):
        self.path = path
        self.exploration = exploration
        self.records = {}
        self._load()

    # ------------------------------------------------------------ learning
    def reward(self, name: str, success: bool = True):
        record = self.records.setdefault(name, {"attempts": 0, "wins": 0})
        record["attempts"] += 1
        if success:
            record["wins"] += 1
        self._save()

    def score(self, candidate: Candidate) -> float:
        record = self.records.get(candidate.name)
        if not record or record["attempts"] == 0:
            return 0.0
        return record["wins"] / record["attempts"]

    def standings(self) -> dict:
        out = {}
        for name, record in self.records.items():
            attempts = record["attempts"]
            out[name] = {
                "attempts": attempts,
                "wins": record["wins"],
                "win_rate": (record["wins"] / attempts) if attempts else 0.0,
            }
        return out

    # ----------------------------------------------------------- selection
    def select(self, candidates: list, scorer=None) -> Candidate:
        """Pick one candidate. Untried candidates are tried first, so
        every option gets a fair trial before the record decides."""
        if not candidates:
            raise ValueError("no candidates to select from")
        score = scorer or self.score
        untried = [c for c in candidates if self._attempts(c.name) == 0]
        pool = untried or list(candidates)
        if self.exploration > 0 and random.random() < self.exploration:
            return random.choice(pool)
        best = max(score(c) for c in pool)
        return next(c for c in pool if score(c) == best)

    def _attempts(self, name: str) -> int:
        return self.records.get(name, {}).get("attempts", 0)

    # ------------------------------------------------------------ storage
    def _save(self):
        with open(self.path, "w") as fh:
            json.dump(self.records, fh, indent=2)

    def _load(self):
        if not os.path.exists(self.path):
            return
        with open(self.path) as fh:
            self.records = json.load(fh)
