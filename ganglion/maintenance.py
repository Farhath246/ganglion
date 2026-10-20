"""
Maintenance - the quiet housekeeping between cycles.

An unbounded history and an unbounded audit log are the two things that
make a long-running system slow down and eventually stop. This trims
both to their configured ceilings. Truncating the audit log keeps its
line hashes self-consistent; only the link to trimmed-off lines is
gone.
"""

import os


class Maintenance:
    def __init__(self, max_history_entries: int = 100, max_audit_lines: int = 1000):
        self.max_history_entries = max_history_entries
        self.max_audit_lines = max_audit_lines

    def run(self, memory, audit_log=None) -> dict:
        result = {}

        history = memory.history
        if len(history) > self.max_history_entries:
            excess = len(history) - self.max_history_entries
            del history[:excess]
            result["trimmed_history"] = excess

        if audit_log is not None:
            trimmed = self._trim_audit(audit_log)
            if trimmed:
                result["trimmed_audit_lines"] = trimmed
        return result

    def _trim_audit(self, audit_log) -> int:
        path = getattr(audit_log, "path", None)
        if not path or not os.path.exists(path):
            return 0
        with open(path) as fh:
            lines = fh.readlines()
        if len(lines) <= self.max_audit_lines:
            return 0
        excess = len(lines) - self.max_audit_lines
        with open(path, "w") as fh:
            fh.writelines(lines[excess:])
        return excess
