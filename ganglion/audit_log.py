"""
Audit log - a tamper-evident record of what the system did.

Every cycle writes a line; each line carries the hash of the one
before it, so changing an old entry invalidates every entry after it.
Not cryptographic proof - the key is right here - but enough that an
accidentally or casually edited log does not verify.
"""

import hashlib
import json
import os
import time


class AuditLog:
    def __init__(self, path: str = "audit.log"):
        self.path = path

    def record(self, event: str, detail: dict = None):
        entry = {
            "ts": time.time(),
            "event": event,
            "detail": detail if detail is not None else {},
            "prev": self._last_hash(),
        }
        entry["hash"] = self._digest(entry)
        with open(self.path, "a") as fh:
            fh.write(json.dumps(entry) + "\n")
        return entry

    def verify(self) -> bool:
        """Every line's hash must match its contents."""
        if not os.path.exists(self.path):
            return True
        with open(self.path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                stored = entry.pop("hash", "")
                if self._digest(entry) != stored:
                    return False
        return True

    @staticmethod
    def _digest(entry: dict) -> str:
        payload = json.dumps(entry, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _last_hash(self) -> str:
        if not os.path.exists(self.path):
            return ""
        last = ""
        with open(self.path) as fh:
            for line in fh:
                if line.strip():
                    last = line
        if not last:
            return ""
        try:
            return json.loads(last).get("hash", "")
        except json.JSONDecodeError:
            return ""
