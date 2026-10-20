"""
Affect - a continuous valence/arousal state that colors every decision.

The amygdala and reward circuits don't evaluate one moment in
isolation; they maintain a running affective state that shifts
gradually with outcomes and modulates the rest of cognition - more
cautious after a string of bad outcomes, more exploratory after good
ones.

This is also where "neuromodulation" (a global dial shifting the whole
system's mode at once) and the "reticular inhibition" idea from an
earlier conversation both land - they're the same underlying mechanism
described three ways, so this one module covers all three rather than
building three overlapping gauges that would all do nearly the same
thing.

Valence: -1 (things are going badly) to +1 (going well).
Arousal: 0 (calm) to 1 (on edge) - rises with hazards and failures,
decays back toward baseline every cycle regardless of outcome.
"""


class Affect:
    def __init__(self, decay: float = 0.1):
        self.valence = 0.0
        self.arousal = 0.0
        self.decay = decay

    def observe(self, success: bool = None, hazard_present: bool = False):
        if success is True:
            self.valence = min(1.0, self.valence + 0.2)
        elif success is False:
            self.valence = max(-1.0, self.valence - 0.3)

        if hazard_present:
            self.arousal = min(1.0, self.arousal + 0.3)

        self.arousal = max(0.0, self.arousal - self.decay)      # calms down over time
        self.valence *= (1 - self.decay / 2)                    # drifts back toward neutral

    def modulation(self) -> dict:
        """How the rest of the system should adjust given current
        affect: more cautious (higher firing threshold, less
        exploration, tighter rate limit) when valence is low or arousal
        is high."""
        caution = max(0.0, -self.valence) * 0.5 + self.arousal * 0.5  # 0..1
        return {
            "threshold_multiplier": 1.0 + caution,
            "exploration_multiplier": max(0.1, 1.0 - caution),
            "rate_multiplier": max(0.2, 1.0 - caution),
        }

    def status(self) -> dict:
        return {"valence": round(self.valence, 3), "arousal": round(self.arousal, 3)}
