"""
Self model - what the system knows about itself.

Two things live here: whether the system is currently well enough to
keep running (too many recent errors and it should stop and let a
human look), and how accurate its predictions have been. Both are
self-knowledge a strategy can consult before committing to a plan.
"""


class SelfModel:
    def __init__(self, max_error_rate: float = 0.3, min_attempts: int = 10):
        self.max_error_rate = max_error_rate
        self.min_attempts = min_attempts
        self.cycles_run = 0
        self.errors = 0
        self.predictions = []

    def record_cycle(self):
        self.cycles_run += 1

    def record_error(self):
        self.errors += 1

    def record_prediction(self, action: str, correct: bool = True):
        self.predictions.append(bool(correct))

    def prediction_accuracy(self) -> float:
        if not self.predictions:
            return 0.0
        return sum(self.predictions) / len(self.predictions)

    def error_rate(self) -> float:
        """Errors over everything attempted - a failed cycle is an
        attempt too, so this stays inside 0..1."""
        return self.errors / max(1, self.cycles_run + self.errors)

    def is_healthy(self, max_error_rate: float = None) -> bool:
        limit = self.max_error_rate if max_error_rate is None else max_error_rate
        if self.cycles_run + self.errors < self.min_attempts:
            return True  # not enough attempts to judge the system by
        return self.error_rate() <= limit

    def status(self) -> dict:
        return {
            "cycles_run": self.cycles_run,
            "errors": self.errors,
            "error_rate": round(self.error_rate(), 3),
            "prediction_accuracy": round(self.prediction_accuracy(), 3),
        }
