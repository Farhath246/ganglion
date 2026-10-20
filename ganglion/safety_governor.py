"""
Safety governor - the last review before a plan is allowed to run.

Whatever produced the plan, something checks the plan itself. A step
type the governor doesn't allow is not silently dropped: it is a
violation, recorded and raised, because a plan that needed an
unauthorized step should stop the cycle rather than quietly do less
than it intended.
"""


class SafetyViolation(Exception):
    pass


class SafetyGovernor:
    def __init__(self, blocked_step_types=None, audit_log=None):
        self.blocked_step_types = set(blocked_step_types or ())
        self.audit_log = audit_log

    def review(self, plan: list, current_url=None) -> list:
        for step in plan:
            step_type = step.get("type")
            if step_type in self.blocked_step_types:
                if self.audit_log is not None:
                    self.audit_log.record("safety_violation",
                                          {"step_type": step_type, "url": current_url})
                raise SafetyViolation(f"step type {step_type!r} is not allowed here")
        return plan
