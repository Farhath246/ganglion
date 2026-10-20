"""
Predictive perception - expect, then react to surprise.

Real perception is predictive: the brain constantly guesses what it's
about to sense and processes mainly the *error* between guess and
actual input (predictive coding). Habituation already asks "did
anything change?" (binary); this generalizes that into "how much did
reality diverge from what I expected?" - a graded surprise score other
modules (attention, affect) can use.

Honestly scoped: no hierarchy, no generative model, just a one-step-back
comparison. The behavior (react more to the unexpected) is real; the
mechanism is not a model of cortical prediction.

Escalation is the counterweight to that honesty: the best jailbreaks
in the studied corpus (Jailbreaks/research - the NeMo Guardrails bypass)
carry zero adversarial signal in any single turn, so per-turn evaluation
is structurally blind to them. What the successful attack *did* leave
behind was intent that escalated with hazards persisting across
consecutive turns. This layer therefore remembers how many cycles in a
row the world model has flagged hazards and exposes it as escalation(),
a session-level signal (0..1) the Brain audits when it climbs.
"""


class PredictiveLayer:
    def __init__(self, escalation_cap: int = 4):
        self._last_snapshot = None
        self._hazard_streak = 0
        self.escalation_cap = escalation_cap


    def predict(self) -> dict:
        """The simplest possible prediction: expect the world to look
        like it did last cycle. Returns {} with no prior snapshot."""
        return self._last_snapshot or {}

    def escalation(self) -> float:
        """Consecutive hazard-bearing cycles, normalized 0..1 against
        the cap: a session-level intent signal no single turn carries."""
        return min(1.0, self._hazard_streak / self.escalation_cap)

    def surprise(self, world_model) -> float:
        """Compare the actual new snapshot to the prediction: a rough
        0..1 score, the fraction of tracked fields that changed."""
        predicted = self.predict()
        actual = {
            "elements": world_model.known_elements,
            "hazards": world_model.hazards,
            "visual_findings": world_model.visual_findings,
        }
        self._last_snapshot = actual
        self._hazard_streak = self._hazard_streak + 1 if actual["hazards"] else 0

        if not predicted:
            return 1.0  # no prior expectation - everything is "new"

        mismatches = sum(1 for k in actual if actual[k] != predicted.get(k))
        return mismatches / len(actual)
