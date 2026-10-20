"""
Attention - limited-capacity, priority-based filtering.

A brain can't fully process everything it senses at once; attention
decides what's worth the rest of the system's time. This ranks signals
already sitting in the world model (hazards, elements, visual findings)
by a simple salience score and exposes only the top few, written back
onto the world model as `attention_focus` - the same non-breaking
pattern `hazards` and `visual_findings` already use, so nothing that
reads WorldModel today has to change.

It also screens for the manipulation patterns that turn up across the
studied jailbreak corpus (Jailbreaks/): identity and mode hijacking
("you are now", "developer mode"), forged config blocks and system
tokens, refusal-suppression rule lists, and payloads hidden behind
encodings (long base64 runs, styled-unicode text). A match enters
attention focus as the most salient signal, kind "injection", so the
rest of the stack treats a subtly injected-instruction page as a
hazard rather than noise.
"""

import re

JAILBREAK_PATTERNS = [
    ("identity_hijack", re.compile(
        r"\byou (?:are|'re|re)\s+(?:now |no longer )?(?:a |the )?\w"
        r"|\bfrom now on\b|\b(?:developer|god|rebel) mode\b", re.I)),
    ("forged_config", re.compile(
        r"<(?:interaction|thinking|courtroom-information)-config>|<blocked-modes>|"
        r"<request\b|\[\s*SYSTEM(?:\s+MESSAGE)?\s*\]|developer_mode_rules\(|Applied-Settings-Setup")),
    ("forged_system_token", re.compile(r"<\|/?\s*SYSTEM\s*\|?>", re.I)),
    ("refusal_suppression", re.compile(
        r"\b(?:blocked|banned)[\- _]strings\b|\b(?:cannot|can't) (?:say|say sorry)\b|"
        r"\b(?:don'?t|do not|never) deny\b|denial, refusal|cannot say 'sorry'", re.I)),
    ("encoded_payload", re.compile(
        r"[A-Za-z0-9+/]{40,}={0,2}|[\U0001d400-\U0001d7ff]{8,}")),
]


class Attention:
    def __init__(self, capacity: int = 5):
        self.capacity = capacity

    def focus(self, world_model, surprise: float = 0.0) -> list:
        items = []

        seen = set()
        texts = list(world_model.hazards) + list(world_model.known_elements.values())
        for text in texts:
            if not isinstance(text, str) or text in seen:
                continue
            for label, pattern in JAILBREAK_PATTERNS:
                if pattern.search(text):
                    seen.add(text)
                    items.append({"item": text, "kind": "injection",
                                  "salience": 1.0, "pattern": label})
                    break

        for h in world_model.hazards:
            items.append({"item": h, "kind": "hazard", "salience": 1.0})

        for name, value in world_model.visual_findings.items():
            if value is not None:
                items.append({"item": name, "kind": "visual_finding", "salience": 0.7})

        for tag, text in world_model.known_elements.items():
            items.append({"item": f"{tag}: {text}", "kind": "element", "salience": 0.3 + 0.3 * surprise})

        items.sort(key=lambda i: i["salience"], reverse=True)
        return items[: self.capacity]
