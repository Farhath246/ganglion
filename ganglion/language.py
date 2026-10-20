"""
Language - turning state into a sentence, and a sentence into a goal.

Production is the system's one outward voice: it takes what happened
this cycle and says it. Comprehension goes the other way, matching an
instruction against the goals the system knows about. Both fail
loudly and specifically, because a production that silently returns
nothing is indistinguishable from a cycle where nothing happened.
"""


class ProductionFailure(Exception):
    pass


class ComprehensionFailure(Exception):
    pass


class Comprehension:
    def __init__(self, known_goals=None):
        self.known_goals = set(known_goals or ())
        self.context = {}

    def understand(self, text: str) -> dict:
        lowered = text.lower()
        for goal in self.known_goals:
            if goal.lower() in lowered:
                return {"goal": goal, "text": text, **self.context}
        raise ComprehensionFailure(f"no known goal found in {text!r}")


class Production:
    def __init__(self, generator=None):
        self.generator = generator

    def say(self, data: dict) -> str:
        try:
            if self.generator is not None:
                return self.generator(data)
            return self._default(data)
        except ProductionFailure:
            raise
        except Exception as exc:
            raise ProductionFailure(str(exc)) from exc

    @staticmethod
    def _default(data: dict) -> str:
        candidate = data.get("candidate") or "no candidate"
        return f"Chose {candidate} with a {data.get('plan_size', 0)}-step plan."
