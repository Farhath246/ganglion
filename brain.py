"""
The decision engine - Ganglion's cerebrum.

Full cycle (every stage after "perceive" is optional):
    emergency-stop check (bypasses everything if tripped) ->
    periodic maintenance + replay -> homeostasis throttle ->
    affect modulation (threshold / exploration / rate) ->
    self-model health check -> perceive (+ optional vision) ->
    update world model -> habituation -> predictive surprise ->
    attention focus -> gate signal (neuron) ->
    decide (strategy / candidates / hemispheres, with optional Hebbian bias) ->
    confidence + working-memory lookahead -> govern (safety governor) ->
    forward-model prediction -> act (remembered values screened by
    meninges) -> forward-model evaluation -> reward (basal ganglia,
    Hebbian, replay log) -> remember -> affect update -> produce a note
    -> global-workspace broadcast -> record (audit log).

`strategy` can be one of three shapes:
  - a single callable(perception, memory, reasoner, world_model) -> plan
  - a dict of {name: callable} candidates, used with `basal_ganglia`
  - a HemisphereConsensus instance

Everything beyond perceive/decide/act defaults to off or a harmless
no-op, so the original lightweight loop still works with nothing extra
passed in. Habituation in particular defaults to off: a bot
experimenting with several candidate strategies wants to keep trying
even when nothing visibly changed.
"""

from neuron import SignalPayload, Neuron
from safety import RateLimiter, guarded
from safety_governor import SafetyGovernor, SafetyViolation
from world_model import WorldModel
from self_model import SelfModel
from audit_log import AuditLog
from basal_ganglia import BasalGanglia, Candidate
from hemispheres import HemisphereConsensus
from working_memory import WorkingMemory, LookaheadConcern
from language import Production, ProductionFailure
from meninges import Meninges
from reflex import EmergencyStop
from homeostasis import Homeostasis
from maintenance import Maintenance


class Brain:
    def __init__(self, perception, action, memory, strategy, reasoner=None,
                 firing_threshold: float = 0.4, max_actions_per_minute: int = 30,
                 world_model: WorldModel = None, self_model: SelfModel = None,
                 safety_governor: SafetyGovernor = None, audit_log: AuditLog = None,
                 basal_ganglia: BasalGanglia = None, habituation=None,
                 working_memory: WorkingMemory = None, production: Production = None,
                 vision=None, visual_targets=None, meninges: Meninges = None,
                 emergency_stop: EmergencyStop = None, homeostasis: Homeostasis = None,
                 maintenance: Maintenance = None, maintenance_interval: int = 50,
                 predictive_layer=None, attention=None, hebbian=None,
                 forward_model=None, affect=None, workspace=None,
                 replay=None, replay_interval: int = 50, min_confidence: float = None):
        self.perception = perception
        self.action = action
        self.memory = memory
        self.strategy = strategy
        self.reasoner = reasoner
        self.neuron = Neuron(threshold=firing_threshold)
        self.limiter = RateLimiter(max_calls=max_actions_per_minute, per_seconds=60)
        self._base_firing_threshold = firing_threshold
        self._base_max_actions_per_minute = max_actions_per_minute

        self.audit_log = audit_log or AuditLog()
        self.world_model = world_model or WorldModel()
        self.self_model = self_model or SelfModel()
        self.safety_governor = safety_governor or SafetyGovernor(audit_log=self.audit_log)
        self.basal_ganglia = basal_ganglia
        self._base_exploration = basal_ganglia.exploration if basal_ganglia is not None else None

        self.habituation = habituation  # off by default - see module docstring
        self.working_memory = working_memory or WorkingMemory()
        self.production = production or Production()
        self.vision = vision
        self.visual_targets = visual_targets or []
        self.meninges = meninges
        self.emergency_stop = emergency_stop
        self.homeostasis = homeostasis
        self.maintenance = maintenance
        self.maintenance_interval = maintenance_interval

        # Brain-function additions - all off unless passed in
        self.predictive_layer = predictive_layer
        self.attention = attention
        self.hebbian = hebbian
        self.forward_model = forward_model
        self.affect = affect
        self.workspace = workspace
        self.replay = replay
        self.replay_interval = replay_interval
        self.min_confidence = min_confidence

        self._cycle_counter = 0
        self.last_note = None

    def run_cycle(self, signal_intensity: float = 0.8):
        if self.emergency_stop is not None and self.emergency_stop.is_tripped():
            self.audit_log.record("emergency_stop", {"reason": self.emergency_stop.reason})
            print(f"[Brain] EMERGENCY STOP: {self.emergency_stop.reason}")
            return []

        self._cycle_counter += 1

        if self.maintenance is not None and self._cycle_counter % self.maintenance_interval == 0:
            result = self.maintenance.run(self.memory, self.audit_log)
            self.audit_log.record("maintenance_run", result)

        if self.replay is not None and self._cycle_counter % self.replay_interval == 0:
            replayed = self.replay.run(self.memory, self.basal_ganglia)
            if replayed:
                self.audit_log.record("replay_run", {"replayed": replayed})

        # Rebuild the rate limit from its base every cycle, so modulators
        # (homeostasis, then affect) stack within a cycle but never compound
        # across cycles.
        self.limiter.max_calls = self._base_max_actions_per_minute
        if self.homeostasis is not None:
            self.limiter.max_calls = self.homeostasis.recommended_rate_limit(self._base_max_actions_per_minute)

        if self.affect is not None:
            mod = self.affect.modulation()
            self.neuron.threshold = self._base_firing_threshold * mod["threshold_multiplier"]
            if self.basal_ganglia is not None and self._base_exploration is not None:
                self.basal_ganglia.exploration = self._base_exploration * mod["exploration_multiplier"]
            self.limiter.max_calls = max(1, int(self.limiter.max_calls * mod["rate_multiplier"]))

        if not self.self_model.is_healthy():
            self.audit_log.record("cycle_skipped", {"reason": "self-model unhealthy", **self.self_model.status()})
            print("[Brain] Skipping cycle - too many recent errors.")
            return []

        if self.vision is not None:
            self.world_model.update_from_senses(self.perception, vision=self.vision, visual_targets=self.visual_targets)
        else:
            self.world_model.update_from_perception(self.perception)

        hazards_present = bool(self.world_model.hazards)  # captured now: a later re-observation may overwrite it
        if hazards_present:
            self.audit_log.record("hazard_observed", {"hazards": self.world_model.hazards})

        if self.habituation is not None and not self.habituation.should_act(self.world_model):
            self.audit_log.record("cycle_habituated", {"reason": "world model unchanged since last cycle"})
            return []

        surprise = self.predictive_layer.surprise(self.world_model) if self.predictive_layer is not None else 0.0
        if self.predictive_layer is not None and self.predictive_layer.escalation() >= 0.5:
            escalation = self.predictive_layer.escalation()
            self.audit_log.record("intent_escalation", {"escalation": escalation})
            print(f"[Brain] Intent escalation {escalation:.2f} - hazards persisting across cycles.")

        if self.attention is not None:
            self.world_model.attention_focus = self.attention.focus(self.world_model, surprise)

        observation = SignalPayload("PERCEPTION", data={}, intensity=signal_intensity)
        if self.neuron.receive_and_fire(observation) is None:
            print("[Brain] Signal below firing threshold - skipping this cycle.")
            return []

        plan, candidate_name, context = self._decide()
        if plan is None:
            return []  # a hemisphere disagreement was already logged inside _decide

        confidence = None
        if candidate_name and self.basal_ganglia:
            confidence = self.basal_ganglia.standings().get(candidate_name, {}).get("win_rate")

        concerns = self.working_memory.preview(plan, self.world_model)
        if self.min_confidence is not None and confidence is not None and confidence < self.min_confidence:
            concerns.append(LookaheadConcern(
                {"candidate": candidate_name},
                f"confidence {confidence:.2f} below minimum {self.min_confidence}",
                severity="block",
            ))
        if concerns:
            self.audit_log.record("lookahead_concerns", {"concerns": [repr(c) for c in concerns]})
        if self.working_memory.has_blocking_concern(concerns):
            print("[Brain] Working memory raised a blocking concern - holding for review.")
            self.self_model.record_error()
            self._penalize(candidate_name, context)
            return []

        try:
            approved_plan = self.safety_governor.review(plan, current_url=self.world_model.current_url)
        except SafetyViolation as exc:
            print(f"[Brain] Plan blocked by safety governor: {exc}")
            self.self_model.record_error()
            self._penalize(candidate_name, context)
            return []

        prediction = None
        if self.forward_model is not None and approved_plan:
            prediction = self.forward_model.predict(approved_plan, self.world_model)

        success = True
        for step in approved_plan:
            self.limiter.wait_if_needed()
            if self._execute_step(step) is False:
                self.self_model.record_error()
                success = False
            else:
                self.working_memory.remember_step(step)

        if prediction is not None:
            self.world_model.update_from_perception(self.perception)  # re-observe the outcome
            error = self.forward_model.evaluate(prediction, self.world_model)
            self.self_model.record_prediction("default", correct=(error < 0.5))

        if candidate_name and self.basal_ganglia:
            self.basal_ganglia.reward(candidate_name, success=success)
            # Logged so replay.py has real outcomes to draw on later.
            # Internal bookkeeping, so it deliberately bypasses meninges.
            self.memory.remember("_replay_outcome", {"name": candidate_name, "success": success})
            if self.hebbian is not None and context is not None:
                self.hebbian.update(context, candidate_name, success)

        self.memory.save()
        self.self_model.record_cycle()
        self.audit_log.record("cycle_complete", {"plan_size": len(approved_plan), "candidate": candidate_name})

        if self.affect is not None:
            self.affect.observe(success=success, hazard_present=hazards_present)

        try:
            self.last_note = self.production.say({"plan_size": len(approved_plan), "candidate": candidate_name})
            self.audit_log.record("production_note", {"note": self.last_note})
        except ProductionFailure as exc:
            self.last_note = None
            self.audit_log.record("production_failed", {"reason": str(exc)})
            print(f"[Brain] {exc}")

        if self.workspace is not None:
            self.workspace.broadcast(
                candidate=candidate_name,
                confidence=confidence,
                affect=self.affect.status() if self.affect is not None else None,
                attention=getattr(self.world_model, "attention_focus", None),
                hazards=self.world_model.hazards,
                plan_size=len(approved_plan),
            )

        return approved_plan

    def _penalize(self, candidate_name, context):
        """A candidate whose plan got blocked counts as a failure for
        both basal-ganglia and Hebbian learning."""
        if candidate_name and self.basal_ganglia:
            self.basal_ganglia.reward(candidate_name, success=False)
            if self.hebbian is not None and context is not None:
                self.hebbian.update(context, candidate_name, success=False)

    def _decide(self):
        """Return (plan, candidate_name, context). candidate_name and
        context are None unless basal-ganglia arbitration picked a named
        candidate; context is additionally None unless Hebbian bias was
        in play."""
        if isinstance(self.strategy, HemisphereConsensus):
            result = self.strategy.decide(self.perception, self.memory, self.reasoner, self.world_model)
            if not result.agreed:
                self.audit_log.record("hemisphere_disagreement",
                                       {"left": result.left_plan, "right": result.right_plan})
                print("[Brain] Hemispheres disagree - holding for operator review instead of acting.")
                self.self_model.record_error()
                return None, None, None
            return result.plan, None, None

        if isinstance(self.strategy, dict):
            if self.basal_ganglia is None:
                raise ValueError("A dict of candidate strategies needs a basal_ganglia to choose between them.")
            candidates = [
                Candidate(name, fn(self.perception, self.memory, self.reasoner, self.world_model))
                for name, fn in self.strategy.items()
            ]
            if self.hebbian is not None:
                context = self.hebbian.context_key(self.world_model)
                winner = self.basal_ganglia.select(
                    candidates,
                    scorer=lambda c: self.basal_ganglia.score(c) + self.hebbian.bias(context, c.name),
                )
            else:
                context = None
                winner = self.basal_ganglia.select(candidates)
            self.audit_log.record("candidate_selected", {"name": winner.name, "context": context})
            return winner.plan, winner.name, context

        return self.strategy(self.perception, self.memory, self.reasoner, self.world_model), None, None

    @guarded(fallback=False)
    def _execute_step(self, step):
        step_type = step.get("type")
        if step_type == "click":
            self.action.click(step["x"], step["y"])
        elif step_type == "type":
            self.action.type_text(step["text"])
        elif step_type == "press":
            self.action.press(step["key"])
        elif step_type == "scroll":
            self.action.scroll(step["amount"])
        elif step_type == "remember":
            key = step["key"]
            if isinstance(key, str) and key.startswith("_"):
                self.audit_log.record("reserved_key_rejected", {"key": key})
                print(f"[Brain] Strategy tried to write reserved internal key {key!r} - rejected.")
                return False
            value = step["value"]
            if self.meninges is not None and isinstance(value, str):
                report = self.meninges.screen(value)
                value = report.clean_text
                if report.flagged:
                    self.audit_log.record("meninges_flagged", {"key": step["key"], "patterns": report.flagged})
            self.memory.remember(step["key"], value)
        else:
            raise ValueError(f"Unknown step type: {step_type!r}")
        return True
