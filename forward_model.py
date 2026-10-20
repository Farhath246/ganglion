"""
Forward model - predict the consequence of an action before it happens.

The cerebellum is thought to run forward models: predicting the sensory
outcome of a movement and correcting for the difference between
prediction and actual result. This does the same thing structurally,
one cycle at a time: before acting, note what's expected to change;
after acting, compare; the mismatch (prediction error) is recorded
against the self-model's reliability for that action - not fed back as
a real-time motor correction, since this controls discrete steps, not
continuous movement.
"""


class ForwardModel:
    def predict(self, plan: list, world_model) -> dict:
        """A deliberately simple prediction: acting should clear any
        currently-flagged hazards and shouldn't introduce new ones.
        Swap this for something richer per action type if needed."""
        return {"expected_hazards_cleared": list(world_model.hazards)}

    def evaluate(self, prediction: dict, world_model_after) -> float:
        """Prediction-error score: 0 (exactly as expected) to 1
        (nothing matched)."""
        expected_cleared = set(prediction.get("expected_hazards_cleared", []))
        if not expected_cleared:
            return 0.0
        still_present = expected_cleared.intersection(world_model_after.hazards)
        return len(still_present) / len(expected_cleared)
