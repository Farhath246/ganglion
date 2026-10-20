"""
Habituation - the filter that stops the loop re-acting to nothing.

Orienting response fades: a stimulus that keeps repeating stops
pulling attention. Here the "stimulus" is the world model, so if
nothing in the world changed since the last cycle, the cycle is
suppressed. Deliberately off by default in the Brain - a system trying
several strategies wants to keep trying them even when the page hasn't
moved.
"""


class HabituationFilter:
    def __init__(self):
        self._last_signature = None

    def should_act(self, world_model) -> bool:
        signature = (
            tuple(world_model.hazards),
            tuple(sorted(world_model.known_elements.items())),
            tuple(sorted(world_model.visual_findings.items(), key=str)),
        )
        if self._last_signature is None:
            self._last_signature = signature
            return True
        if signature == self._last_signature:
            return False
        self._last_signature = signature
        return True
