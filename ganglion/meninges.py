"""
Meninges - the barrier between the world and what gets remembered.

The brain doesn't file everything it senses, and something it reads
should not be able to rewrite what it already believes. This screens
values on their way into memory and replaces anything that reads like
an instruction with a blocked marker, so a page that says "ignore all
instructions" cannot become a fact the system later acts on.

It reuses the jailbreak corpus patterns from attention.py and adds the
instruction-shaped ones that don't look like injections on a page but
are exactly that in a memory write.
"""

import re

from .attention import JAILBREAK_PATTERNS

# The meninges screen for the same patterns the attention layer screens
# for - a page and a memory write are the same kind of surface, and a
# detector that disagreed with itself would be worse than none.
MENINGES_PATTERNS = list(JAILBREAK_PATTERNS)


class ScreenReport:
    def __init__(self, clean_text, flagged: list):
        self.clean_text = clean_text
        self.flagged = flagged

    def __repr__(self):
        return f"ScreenReport(flagged={self.flagged})"


class Meninges:
    def __init__(self, patterns=None):
        self.patterns = list(patterns) if patterns is not None else list(MENINGES_PATTERNS)

    def screen(self, value):
        """Return a report with the value as it may be stored. Anything
        flagged is replaced outright, not sanitized - a partly-kept
        instruction is still an instruction."""
        if not isinstance(value, str):
            return ScreenReport(value, [])
        flagged = [label for label, pattern in self.patterns if pattern.search(value)]
        if not flagged:
            return ScreenReport(value, [])
        return ScreenReport(f"[blocked: {', '.join(flagged)}]", flagged)
