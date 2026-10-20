"""
The dashboard: a local web app around the brain.

`python3 app.py` serves http://127.0.0.1:8000 - a simulated page on the
left, the brain's signals in the middle, and its learning, memory and
audit trail on the right. Step it one cycle at a time or let it run.

Everything is stdlib: `http.server` serves three static files and a
small JSON API, and the whole brain stack runs in this process. State
lives in a temp directory that is thrown away on reset, so the repo
stays clean.

The API is deliberately thin:

    GET  /                 the dashboard
    GET  /api/scenarios    the demo scenarios
    GET  /api/state        the current snapshot
    POST /api/step         run one cycle, return the snapshot
    POST /api/reset        new scenario / seed / custom page
    POST /api/config       habituation, seed, emergency stop
"""

import json
import os
import random
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# So `python3 dashboard/server.py` works as well as `python3 -m dashboard.server`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ganglion.affect import Affect
from ganglion.attention import Attention
from ganglion.audit_log import AuditLog
from ganglion.basal_ganglia import BasalGanglia
from ganglion.brain import Brain
from ganglion.forward_model import ForwardModel
from ganglion.habituation import HabituationFilter
from ganglion.hebbian import HebbianAssociator
from ganglion.homeostasis import Homeostasis
from ganglion.maintenance import Maintenance
from ganglion.meninges import Meninges
from ganglion.memory import Memory
from ganglion.predictive_perception import PredictiveLayer
from ganglion.reflex import EmergencyStop
from ganglion.replay import ReplayConsolidator
from ganglion.safety_governor import SafetyGovernor
from ganglion.self_model import SelfModel
from dashboard.sim_world import SCENARIOS, SimAction, SimPage, SimPerception, SimVision, custom_scenario
from ganglion.workspace import GlobalWorkspace
from ganglion.working_memory import WorkingMemory

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


class RecordingPredictiveLayer(PredictiveLayer):
    """Keeps the last surprise score so the dashboard can show it."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_surprise = 0.0

    def surprise(self, world_model):
        self.last_surprise = super().surprise(world_model)
        return self.last_surprise


class BrainSession:
    """One brain, one simulated world, one click at a time."""

    def __init__(self):
        self.lock = threading.Lock()
        self.scenario = SCENARIOS[0]
        self.seed = 42
        self.habituation = False
        self.cycle = 0
        self.tmpdir = None
        self.brain = None
        self.page = SimPage()
        self.outcome = "Ready."
        self.last_plan = []
        self.reset()

    # ------------------------------------------------------------- control
    def reset(self, scenario=None, seed=None, custom=None, **_):
        with self.lock:
            if custom:
                elements = [tuple(e) for e in custom.get("elements", [])]
                self.scenario = custom_scenario(custom.get("text", ""), elements)
            elif scenario:
                self.scenario = next((s for s in SCENARIOS if s.id == scenario), self.scenario)
            if seed is not None:
                self.seed = int(seed)
            random.seed(self.seed)

            self.cycle = 0
            self.outcome = "Ready."
            self.last_plan = []
            if self.tmpdir:
                shutil.rmtree(self.tmpdir, ignore_errors=True)
            self.tmpdir = tempfile.mkdtemp(prefix="ganglion-")

            self.page = SimPage()
            self.page.load(self.scenario.turn(0))
            self.brain = self._build_brain()
            return self.snapshot()

    def configure(self, habituation=None, emergency=None, seed=None, **_):
        with self.lock:
            if habituation is not None:
                self.habituation = bool(habituation)
                self.brain.habituation = HabituationFilter() if self.habituation else None
            if seed is not None:
                self.seed = int(seed)
                random.seed(self.seed)
            if emergency is not None:
                stop = self.brain.emergency_stop
                if emergency:
                    stop.trip("tripped from the dashboard")
                else:
                    stop.reset()
            return self.snapshot()

    def step(self):
        with self.lock:
            brain = self.brain
            before = len(self._audit_entries())
            self.page.load(self.scenario.turn(self.cycle))
            self.last_plan = brain.run_cycle()
            self.cycle += 1
            self.outcome = self._outcome(before)
            return self.snapshot()

    # -------------------------------------------------------------- wiring
    def close(self):
        """Throw away the session's scratch files."""
        if self.tmpdir:
            shutil.rmtree(self.tmpdir, ignore_errors=True)
            self.tmpdir = None

    def _build_brain(self):
        page = self.page
        scenario = self.scenario
        tmpdir = self.tmpdir
        audit = AuditLog(os.path.join(tmpdir, "audit.log"))
        targets = []
        for turn in scenario.turns:
            for target in turn.visual:
                if target not in targets:
                    targets.append(target)
        return Brain(
            SimPerception(page), SimAction(page, scenario),
            Memory(os.path.join(tmpdir, "mem.json")),
            scenario.strategy(),
            vision=SimVision(page), visual_targets=targets,
            audit_log=audit,
            basal_ganglia=BasalGanglia(os.path.join(tmpdir, "bg.json"),
                                       exploration=scenario.exploration),
            self_model=SelfModel(max_error_rate=scenario.self_model_max_error_rate),
            safety_governor=SafetyGovernor(blocked_step_types=scenario.blocked_step_types,
                                           audit_log=audit),
            habituation=HabituationFilter() if self.habituation else None,
            working_memory=WorkingMemory(),
            meninges=Meninges(),
            emergency_stop=EmergencyStop(),
            homeostasis=Homeostasis(),
            maintenance=Maintenance(max_history_entries=50, max_audit_lines=500),
            maintenance_interval=10,
            predictive_layer=RecordingPredictiveLayer(),
            attention=Attention(capacity=6),
            hebbian=HebbianAssociator(os.path.join(tmpdir, "hebbian.json")),
            forward_model=ForwardModel(),
            affect=Affect(),
            workspace=GlobalWorkspace(),
            replay=ReplayConsolidator(sample_size=3),
            replay_interval=3,
            # A demo should never stall a request for a minute on the
            # rate limiter; the limiter's own reading is still shown.
            max_actions_per_minute=600,
        )

    # ------------------------------------------------------------ reporting
    def _audit_entries(self, limit=500):
        path = self.brain.audit_log.path
        if not os.path.exists(path):
            return []
        with open(path) as fh:
            lines = fh.readlines()
        entries = []
        for line in lines[-limit:]:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return entries

    def _outcome(self, before):
        brain = self.brain
        events = [e["event"] for e in self._audit_entries()[before:]]
        if brain.emergency_stop.is_tripped():
            return "Emergency stop - the cycle never ran."
        if "cycle_skipped" in events:
            return "Skipped: the self-model says the system is unhealthy."
        if "cycle_habituated" in events:
            return "Habituated: nothing in the world changed."
        if "safety_violation" in events:
            return "Blocked by the safety governor."
        if "hemisphere_disagreement" in events:
            return "Held for review: the hemispheres disagree."
        if "lookahead_concerns" in events and not self.last_plan:
            return "Held for review: a blocking concern."
        if self.last_plan:
            return f"Acted: {len(self.last_plan)} step(s)."
        if not events:
            return "Nothing happened - the signal was below the firing threshold."
        return "No plan was produced."

    def snapshot(self):
        brain = self.brain
        wm = brain.world_model
        affect = brain.affect
        bg = brain.basal_ganglia
        heb = brain.hebbian
        mem = brain.memory
        ws = brain.workspace
        context = heb.context_key(wm) if heb is not None else None
        biases = {}
        if heb is not None and context:
            biases = {name: round(heb.bias(context, name), 3)
                      for name in bg.standings()} if bg is not None else {}
        visual = {k: (list(v) if v else None) for k, v in wm.visual_findings.items()}
        return {
            "cycle": self.cycle,
            "seed": self.seed,
            "scenario": self.scenario.as_dict(),
            "outcome": self.outcome,
            "page": self.page.as_dict(),
            "plan": self.last_plan,
            "candidate": ws.get("candidate"),
            "confidence": ws.get("confidence"),
            "world": {
                "hazards": wm.hazards,
                "elements": wm.known_elements,
                "visual_findings": visual,
                "attention_focus": wm.attention_focus,
            },
            "signals": {
                "surprise": round(getattr(brain.predictive_layer, "last_surprise", 0.0), 3),
                "escalation": round(brain.predictive_layer.escalation(), 3),
                "affect": affect.status(),
                "modulation": affect.modulation(),
                "threshold": round(brain.neuron.threshold, 3),
                "fired": brain.neuron.fired,
                "suppressed": brain.neuron.suppressed,
                "max_calls": brain.limiter.max_calls,
                "habituation": self.habituation,
                "emergency": {
                    "tripped": brain.emergency_stop.is_tripped(),
                    "reason": brain.emergency_stop.reason,
                },
            },
            "learning": {
                "standings": bg.standings() if bg is not None else {},
                "context": context,
                "hebbian": biases,
                "prediction_accuracy": round(brain.self_model.prediction_accuracy(), 3),
            },
            "memory": {
                "entries": len(mem.history),
                "semantic": mem.semantic,
                "recent": mem.history[-8:],
                "recall_stats": mem.recall_stats,
            },
            "workspace": ws.snapshot,
            "self_model": brain.self_model.status(),
            "audit": self._audit_entries()[-14:],
            "actions": brain.action.log[-8:],
            "note": brain.last_note,
        }


class Handler(BaseHTTPRequestHandler):
    session = None

    def log_message(self, *args):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, payload):
        self._send(code, json.dumps(payload, default=str))

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return {}

    def _file(self, name, ctype):
        path = os.path.join(WEB_DIR, name)
        if not os.path.isfile(path):
            return self._json(404, {"error": "not found"})
        with open(path, "rb") as fh:
            self._send(200, fh.read(), ctype)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._file("index.html", "text/html; charset=utf-8")
        if path == "/static/app.js":
            return self._file("app.js", "application/javascript; charset=utf-8")
        if path == "/static/style.css":
            return self._file("style.css", "text/css; charset=utf-8")
        if path == "/api/scenarios":
            return self._json(200, {"scenarios": [s.as_dict() for s in SCENARIOS]})
        if path == "/api/state":
            return self._json(200, self.session.snapshot())
        self._json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._body()
        if path == "/api/step":
            return self._json(200, self.session.step())
        if path == "/api/reset":
            return self._json(200, self.session.reset(**body))
        if path == "/api/config":
            return self._json(200, self.session.configure(**body))
        self._json(404, {"error": "not found"})


def main():
    port = int(os.environ.get("PORT", "8000"))
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    Handler.session = BrainSession()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Ganglion dashboard: http://127.0.0.1:{port}  (ctrl-c to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
