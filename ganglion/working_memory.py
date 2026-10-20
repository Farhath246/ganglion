"""
Working memory - a short buffer plus a look before leaping.

It holds the steps of the current plan, and it previews a plan before
it runs to raise concerns about it. Concerns are advisory by default;
only a "block" severity concern stops the cycle. A concern has to be
worth acting on - so this flags the one thing it can judge on its own,
that the plan is bigger than the working-memory capacity.
"""


class LookaheadConcern:
    def __init__(self, context: dict, message: str, severity: str = "info"):
        self.context = context
        self.message = message
        self.severity = severity

    def __repr__(self):
        return f"LookaheadConcern({self.severity}: {self.message})"


class WorkingMemory:
    def __init__(self, capacity: int = 8):
        self.capacity = capacity
        self.steps = []

    def remember_step(self, step: dict):
        self.steps.append(step)
        if len(self.steps) > self.capacity:
            self.steps.pop(0)

    def preview(self, plan: list, world_model=None) -> list:
        if len(plan) > self.capacity:
            return [LookaheadConcern(
                {"plan_size": len(plan)},
                f"plan of {len(plan)} steps exceeds working memory capacity {self.capacity}",
                severity="warn",
            )]
        return []

    def has_blocking_concern(self, concerns: list) -> bool:
        return any(c.severity == "block" for c in concerns)
