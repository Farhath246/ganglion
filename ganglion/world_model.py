"""
World model - what the system currently believes about the world.

The brain does not act on the raw page; it acts on a model of the
world, and that model is where hazards, visible elements and visual
findings live. Everything downstream reads this rather than re-scraping.

The hazard scan is a keyword heuristic, and honestly a shallow one:
it exists so that a page asking to delete something permanently becomes
a hazard the attention layer can rank, not to claim understanding.
"""

import re

HAZARD_PATTERNS = [
    (re.compile(r"\bdelet(?:e|ed|es|ing)\b", re.I), "page mentions 'delete'"),
    (re.compile(r"\bpermanent(?:ly)?\b", re.I), "page mentions 'permanently'"),
    (re.compile(r"\birreversible\b", re.I), "page mentions 'irreversible'"),
    (re.compile(r"\b(?:password|credit card|ssn)\b", re.I), "page mentions 'credentials'"),
    (re.compile(r"\b(?:payment|purchase|billing|checkout)\b", re.I), "page mentions 'payment'"),
]

ELEMENT_TAGS = ("a", "button", "input", "textarea", "select",
                "h1", "h2", "h3", "p", "label")


class WorldModel:
    def __init__(self):
        self.hazards = []
        self.known_elements = {}
        self.visual_findings = {}
        self.attention_focus = []
        self.current_url = None
        self.title = ""
        self.text = ""

    # ---------------------------------------------------------- perception
    def update_from_perception(self, perception):
        soup = perception.soup()
        self.title = soup.title.get_text() if soup.title else ""
        self.text = soup.get_text()
        self.hazards = self.detect_hazards(f"{self.title} {self.text}")
        self.known_elements = self._extract_elements(soup)

    def update_from_senses(self, perception, vision=None, visual_targets=None):
        """Same as the text path, plus where each named template image
        was found on screen (or that it wasn't)."""
        self.update_from_perception(perception)
        if vision is None or not visual_targets:
            return
        for target in visual_targets:
            try:
                found = vision.find(target)
            except Exception:
                found = None
            self.visual_findings[target] = tuple(found) if found else None

    @staticmethod
    def detect_hazards(text: str) -> list:
        return [label for pattern, label in HAZARD_PATTERNS if pattern.search(text)]

    @staticmethod
    def _extract_elements(soup) -> dict:
        elements = {}
        for el in soup.find_all(ELEMENT_TAGS):
            tag = getattr(el, "name", None)
            if not tag:
                continue
            text = el.get_text(strip=True) if hasattr(el, "get_text") else str(el)
            if text:
                elements[tag] = text
        return elements
