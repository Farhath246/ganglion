"""
Reflex - the emergency stop.

The fastest path in a nervous system: no deliberation, no strategy, no
memory. When something is wrong enough that no amount of thinking about
it helps, the whole loop halts. This is that switch, and it sits above
every other stage of the cycle.
"""


class EmergencyStop:
    def __init__(self):
        self.tripped = False
        self.reason = None

    def trip(self, reason: str = "unspecified"):
        self.tripped = True
        self.reason = reason

    def reset(self):
        self.tripped = False
        self.reason = None

    def is_tripped(self) -> bool:
        return self.tripped
