"""
Global workspace - a per-cycle broadcast of what's currently salient.

Global Workspace Theory proposes that a limited amount of information
wins a competition each moment and gets broadcast to the whole system
at once, and that this broadcast is what turns many separate,
unconscious processes into one coherent, reportable stream.

This module is explicitly NOT a claim to implement consciousness - that
remains a genuinely open problem in neuroscience, not a missing feature
with an available API. This is only the structural pattern underneath
the theory: a single shared object, rebuilt each cycle, that any module
can read from instead of each one separately querying several others. A
blackboard, not a mind.
"""


class GlobalWorkspace:
    def __init__(self):
        self.snapshot = {}

    def broadcast(self, **items):
        """Replace the workspace with this cycle's winning signals."""
        self.snapshot = items

    def get(self, key, default=None):
        return self.snapshot.get(key, default)
