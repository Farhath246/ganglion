"""
Neuron - the threshold gate.

A real neuron fires when incoming drive crosses a threshold; below it,
the signal dies out. This is that gate and nothing more: it does not
sum inputs, does not spike, does not learn. The Brain raises the
threshold when affect says "be careful" and lowers it when the system
is confident, which is the whole of its neuromodulation story.
"""


class SignalPayload:
    def __init__(self, kind: str, data: dict = None, intensity: float = 1.0):
        self.kind = kind
        self.data = data or {}
        self.intensity = intensity

    def __repr__(self):
        return f"SignalPayload({self.kind!r}, intensity={self.intensity})"


class Neuron:
    def __init__(self, threshold: float = 0.4):
        self.threshold = threshold
        self.fired = 0
        self.suppressed = 0

    def receive_and_fire(self, payload: SignalPayload):
        """Return the payload if it crosses the threshold, else None."""
        if payload.intensity < self.threshold:
            self.suppressed += 1
            return None
        self.fired += 1
        return payload
