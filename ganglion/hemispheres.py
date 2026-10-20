"""
Hemispheres - two independent proposals, and the disagreement between them.

Two strategies see the same world and produce two plans. If they agree
on what to do, the plan runs. If they don't, the system doesn't pick a
winner by fiat - it holds, and asks a human. Agreement is judged on
the shape of the plan (same steps, same destinations) rather than on
identical values, since two routes to the same place is agreement, not
a conflict.
"""


class Consensus:
    def __init__(self, agreed: bool, plan, left_plan, right_plan):
        self.agreed = agreed
        self.plan = plan
        self.left_plan = left_plan
        self.right_plan = right_plan


class HemisphereConsensus:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def decide(self, perception, memory, reasoner, world_model) -> Consensus:
        left_plan = self.left(perception, memory, reasoner, world_model)
        right_plan = self.right(perception, memory, reasoner, world_model)
        agreed = _shape(left_plan) == _shape(right_plan)
        return Consensus(agreed=agreed,
                         plan=left_plan if agreed else None,
                         left_plan=left_plan,
                         right_plan=right_plan)


def _shape(plan) -> list:
    """A plan's structure, ignoring the values it carries."""
    return [(step.get("type"), step.get("key")) for step in plan or []]
