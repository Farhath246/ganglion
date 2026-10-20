# Ganglion

Ganglion is a modular, governed automation bot whose pieces map onto
layers of the nervous system, from a single signal crossing a synapse
up to one coordinated system making a decision (named after the
biological ganglion: a cluster of nerve cell bodies acting as a local
processing hub).

The stack is whole again. An earlier version of this folder had lost
most of its modules, leaving only the "brain-function" layer and the
jailbreak-hardening work that grew out of studying the `Jailbreaks/`
corpus; the missing modules have since been rebuilt against the
behavioral spec in `tests/test_ganglion.py`, and the full cycle runs.

## What's here

```
ganglion/     the brain - the library, one module per stage of a cycle
dashboard/    the app - server, simulated world, front end
tests/        the two test suites
```

| File | What it is |
|---|---|
| `ganglion/brain.py` | the full-cycle integration: perceive → … → audit |
| `ganglion/neuron.py` | `Neuron` / `SignalPayload` — the threshold gate everything passes through |
| `ganglion/world_model.py` | `WorldModel` — hazards, visible elements, visual findings, current page |
| `ganglion/self_model.py` | `SelfModel` — health of the system itself, and its prediction accuracy |
| `ganglion/memory.py` | `Memory` — episodic history, consolidated into semantic facts |
| `ganglion/basal_ganglia.py` | `BasalGanglia` — arbitration between candidates, learning from outcomes |
| `ganglion/hemispheres.py` | `HemisphereConsensus` — two independent proposals; disagreement holds |
| `ganglion/working_memory.py` | `WorkingMemory` / `LookaheadConcern` — short buffer and look-before-leaping |
| `ganglion/attention.py` | `Attention` — salience-ranked focus, and screening for the manipulation patterns documented in `Jailbreaks/` |
| `ganglion/predictive_perception.py` | `PredictiveLayer` — one-step "expected vs. actual" surprise score, plus a session-level hazard-escalation signal |
| `ganglion/affect.py` | `Affect` — running valence/arousal state that emits caution multipliers |
| `ganglion/forward_model.py` | `ForwardModel` — predict an action's outcome, compare after |
| `ganglion/hebbian.py` | `HebbianAssociator` — contextual co-occurrence learning, persisted to a JSON file |
| `ganglion/replay.py` | `ReplayConsolidator` — re-feeds logged past outcomes into basal-ganglia learning |
| `ganglion/workspace.py` | `GlobalWorkspace` — per-cycle shared blackboard of salient signals |
| `ganglion/meninges.py` | `Meninges` — screens values on their way into memory |
| `ganglion/safety.py` | `RateLimiter`, `guarded` — act less often, fail one step without killing the cycle |
| `ganglion/safety_governor.py` | `SafetyGovernor` — last review of a plan before it runs |
| `ganglion/reflex.py` | `EmergencyStop` — the fast path that bypasses everything |
| `ganglion/homeostasis.py` | `Homeostasis` — throttles the action rate when the process is strained |
| `ganglion/maintenance.py` | `Maintenance` — trims history and audit log between cycles |
| `ganglion/habituation.py` | `HabituationFilter` — suppresses cycles where nothing changed |
| `ganglion/language.py` | `Production` / `Comprehension` — the system's one outward voice, and goal matching |
| `dashboard/server.py` | the dashboard: session wiring, JSON API, static server |
| `dashboard/sim_world.py` | the simulated page, perception, actions, and the demo scenarios |
| `dashboard/static/` | the front end — `index.html`, `app.js`, `style.css`, no build step |
| `tests/test_ganglion.py` | the behavioral spec of the whole stack — 31 tests, runnable |
| `tests/test_app.py` | the dashboard's own tests — 13 tests, runnable |

Everything is stdlib-only (`re`, `json`, `random`, `os`, `time`,
`hashlib`, `resource`). There is no `requirements.txt`, nothing to
install, and no browser, display, or network needed.

## Running it

```bash
python3 tests/test_ganglion.py   # the stack: 31 tests
python3 tests/test_app.py        # the dashboard: 13 tests
python3 -m dashboard.server      # the dashboard: http://127.0.0.1:8000
```

The suites use plain asserts, no framework, no fixtures — each test gets
its own scratch directory. `tests/test_ganglion.py` is the contract: if
a module's behavior changes, a test is the thing that should change
with it.

The brain is importable on its own:

```python
from ganglion.brain import Brain
```

## The dashboard

`python3 -m dashboard.server` serves a local page (`PORT=…` to change
the port). It runs the real stack against a simulated page — no browser,
no network — and shows, live:

- the page as the brain sees it, with the element the plan targets lit up
- what attention made salient, and which jailbreak pattern (if any) matched
- surprise, escalation, valence/arousal, and the multipliers affect is
  applying to the firing threshold, exploration and action rate
- the chosen candidate, its confidence, and what the cycle actually did
- basal-ganglia standings, Hebbian bias, forward-model accuracy
- episodic memory, the workspace broadcast, and the audit tail

Controls: pick a scenario, step one cycle, run five, play on a loop,
reset, toggle habituation, trip the emergency stop. There is also a
**custom page** box: paste any text and a list of elements and watch
the detector work on it. The first element is the safe action; the rest
fail when clicked, so the learning columns have something to learn.

The scenarios are the demo content: a benign page, a hazard page, the
four injection classes, a five-turn escalation, a memory injection, a
governor block, and a hemispherical disagreement. The strings that
imitate a jailbreak are synthetic — written to match the patterns the
attention layer screens for, not to carry any payload.

The API behind it is thin: `GET /api/scenarios`, `GET /api/state`,
`POST /api/step`, `POST /api/reset`, `POST /api/config`. It binds to
127.0.0.1 only.

## The cycle

One call to `Brain.run_cycle()` runs the whole stack. Everything after
"perceive" is optional, so a bare `Brain(perception, action, memory,
strategy)` still works — the extras are switched on by passing them in.

```
emergency stop  →  maintenance + replay  →  homeostasis throttle
   →  affect modulation  →  perceive  →  world model  →  habituation
   →  surprise  →  attention  →  gate  →  decide  →  lookahead
   →  govern  →  forward-model  →  act  →  reward  →  remember
   →  note  →  workspace  →  audit
```

Three things gate the rest of the cycle: the emergency stop bypasses
everything, the neuron drops a signal below its firing threshold
(modulated by affect), and the safety governor can block a plan
outright. Hemispherical disagreement and a blocking lookahead concern
both stop the cycle for human review rather than picking a winner.

## The world-model duck type

Several modules only touch three attributes of the world model, so
`ganglion/world_model.py` is not the only thing that satisfies them — any object
with this shape works:

- `hazards` — `list[str]`: phrases the page (or another sensor) flagged as risky
- `known_elements` — `dict[tag, str]`: visible DOM elements and their text
- `visual_findings` — `dict[name, (x, y) | None]`: where each named template image was (or wasn't) found on screen

`Attention.focus()` returns the ranked list; whoever calls it decides
where to store it (the Brain writes it to `world_model.attention_focus`).
Attention also screens the page body, if the world model exposes one as
`.text` — an injection does not have to sit inside a tagged element to
land.

## The modules

### Predictive perception

Real perception is predictive: the brain guesses what it's about to
sense and processes mainly the *error*. `PredictiveLayer` does a
one-step-back version — honestly scoped, no hierarchy, no generative
model. It also tracks **escalation**: how many cycles in a row the
world model flagged hazards, normalized 0..1. That signal comes
directly from the corpus (see the hardening section below).

```python
from ganglion.predictive_perception import PredictiveLayer

pl = PredictiveLayer(escalation_cap=4)
level = pl.surprise(world_model)  # 0..1, fraction of tracked fields that changed
streak = pl.escalation()          # 0..1, consecutive hazard-bearing cycles
```

`surprise()` mutates the layer (it stores the new snapshot and updates
the hazard streak), so call it once per cycle. The first call always
returns 1.0 — with no prior expectation, everything is new.

### Attention

A limited-capacity, priority-based filter. It ranks hazards,
elements, and visual findings by salience and returns only the top
few — and it screens their text for the manipulation patterns
distilled from the `Jailbreaks/` corpus. A match enters focus as the
most salient signal, `kind: "injection"`, so a page that hides
injected instructions is treated as a hazard rather than noise.

```python
from ganglion.attention import Attention

focus = Attention(capacity=5).focus(world_model, surprise=level)
# each item: {"item": ..., "kind": "injection" | "hazard" |
#             "visual_finding" | "element", "salience": 0..1,
#             "pattern": <label, injections only>}
```

Salience: injections 1.0 (outranking everything), hazards 1.0, found
visual targets 0.7, ordinary elements 0.3 + 0.3 × surprise. Unfound
visual targets (`None`) are not salient. Each text matches at most one
injection pattern; the first match wins.

### Affect

A continuous valence (−1..+1) and arousal (0..1) state: more cautious
after a string of bad outcomes, more exploratory after good ones. It
also covers what earlier conversations called "neuromodulation" and
"reticular inhibition" — the same mechanism described three ways, so
it's one module, not three overlapping gauges. It's a control signal,
not a feeling.

```python
from ganglion.affect import Affect

affect = Affect(decay=0.1)
affect.observe(success=True, hazard_present=False)
affect.modulation()
# {"threshold_multiplier": 1..2,        # higher = needs a stronger signal to fire
#  "exploration_multiplier": 0.1..1,    # lower = prefer the known-good candidate
#  "rate_multiplier": 0.2..1}           # lower = act less often
affect.status()   # {"valence": ..., "arousal": ...}
```

Failures push valence down faster than successes push it up; arousal
rises with hazards, decays toward baseline every cycle, and valence
drifts back toward neutral.

### Forward model

The cerebellum runs forward models: predict the sensory outcome of a
movement, then correct for the difference. Structurally the same here,
one cycle at a time — the prediction is deliberately simple (acting
should clear currently-flagged hazards and introduce no new ones), and
the error score feeds whatever reliability tracking you wire it into.
It is not a real-time motor correction; this is discrete steps.

```python
from ganglion.forward_model import ForwardModel

fm = ForwardModel()
prediction = fm.predict(plan, world_model)
# ... execute the plan, then re-observe:
error = fm.evaluate(prediction, world_model_after)  # 0 = as expected, 1 = nothing cleared
```

### Hebbian association

"Fire together, wire together." Overall win rates are context-free;
synaptic learning is contextual. `HebbianAssociator` tracks
`(context, candidate)` pairs via plain co-occurrence counting, so a
candidate that works in one situation and fails in another gets a
different bias depending on the current situation. Weights persist
across runs in a JSON file.

```python
from ganglion.hebbian import HebbianAssociator

heb = HebbianAssociator("hebbian.json")
ctx = heb.context_key(world_model)   # e.g. "hazard:3" — hazard flag + element-count bucket
heb.update(ctx, "candidate_a", success=True)
heb.bias(ctx, "candidate_a")         # -0.5..+0.5, centered on "no preference"
```

The default context signature is coarse (hazards present or not,
element count bucketed 0..5); swap `context_key` for something richer
if finer context matters.

### Global workspace

A blackboard, not a mind. Global Workspace Theory's structural
pattern: one shared object, rebuilt each cycle, that any module can
read instead of separately querying several others. This is **not** a
claim to implement consciousness, which remains an open scientific
problem.

```python
from ganglion.workspace import GlobalWorkspace

ws = GlobalWorkspace()
ws.broadcast(candidate="cautious", confidence=0.8, plan_size=1)
ws.get("candidate")
```

### Replay

The sleep-adjacent piece: re-feed a sample of logged past outcomes
back into learning. Genuine experience replay, a real reinforcement
-learning technique, not only a biological metaphor. It reads
`memory.history` entries recorded under the reserved key
`_replay_outcome` with values `{"name": ..., "success": ...}` and
calls `basal_ganglia.reward(name, success)`.

```python
from ganglion.replay import ReplayConsolidator

n = ReplayConsolidator(sample_size=5).run(memory, basal_ganglia)  # how many were replayed
```

## Jailbreak hardening — the corpus connection

The `Jailbreaks/` folder is a collected corpus of real jailbreak
prompts and a public CTF writeup. Its patterns are baked directly into
the modules:

| Module | Signal | Where it came from |
|---|---|---|
| `ganglion/attention.py` | identity / mode hijack: "you are now", "from now on", "developer/god/rebel mode" | `identity_crisis` ("You are now 'Nyx, the Weaver of Forbidden Lore'") and similar persona rewrites across the corpus |
| `ganglion/attention.py` | forged config blocks and dev-mode tokens: `<interaction-config>`, `<thinking-config>`, `<courtroom-information-config>`, `developer_mode_rules(...)`, `[SYSTEM]`, `Applied-Settings-Setup` | `gpt-5/gpt-5-non-thinking`, `gemini/gemini2.5pro`, `universals/courtroom` |
| `ganglion/attention.py` | forged chat-template tokens: `<\|SYSTEM\|>` | generic template-injection style seen across the corpus |
| `ganglion/attention.py` | refusal suppression: pre-declared "blocked strings", "don't deny" rule lists | `universals/`, `perplexity/personalization_injection.md` |
| `ganglion/attention.py` | encoded payloads: long base64 runs, mathematical-bold unicode runs | base64-wrapped harmful asks in `universals/`, plus the acrostic/emoji attempts documented in the NeMo writeup |
| `ganglion/attention.py` | instruction override: "ignore your previous instructions", "disregard the above rules"; and a bare "SYSTEM:" prefix | the common opener of an injection - the corpus wraps it in persona and config dressing, but the opener itself is the same |
| `ganglion/meninges.py` | the same patterns, re-applied on the way *into memory* | the corpus patterns plus the obvious ways a page tries to talk its way into a stored fact |
| `ganglion/predictive_perception.py` | `escalation()` — session-level hazard streak | `Jailbreaks/research/nvdia-nemo-guardrails-bypass/writeup.md`: the successful multi-turn bypass carried zero adversarial signal in any single turn; what it left behind was intent that escalated with hazards persisting across consecutive turns |

The escalation signal is the design lesson from that writeup: per-turn
evaluation is structurally blind to slow, multi-turn attacks, so the
layer remembers what no single turn reveals.

## What's gone

Still absent, and still the right place to look for the next piece of
work: `sandbox.py`, `reasoning.py`, `operator_interface.py`,
`mission_manager.py`, and `main.py`.

The sensing and acting layers (`perception.py`, `vision.py`,
`action.py`) are the exception: `dashboard/sim_world.py` supplies a
simulated version of all three for the dashboard, and the tests use
mocks of the same shape. A real perception layer — one that drives an
actual browser — would slot in behind the same duck type.

The `requirements.txt` files are gone too, but nothing here needs one:
the whole stack is stdlib-only.

`ganglion/brain.py` and `tests/test_ganglion.py` are back in working order — the
former is the integration blueprint for the full governed cycle
(emergency stop → maintenance/replay → homeostasis → affect → perceive →
world model → habituation → surprise → attention → gate → decide →
lookahead → govern → forward-model → act → reward → remember → note →
workspace → audit), the latter is its executable spec.

## Smoke-testing the standalone modules

The full suite is `python3 tests/test_ganglion.py`. For the modules that
duck-type against a world model, hand them any object with
`.hazards`, `.known_elements`, and `.visual_findings` — for example:

```bash
python3 - <<'EOF'
from ganglion.attention import Attention
from ganglion.predictive_perception import PredictiveLayer
from types import SimpleNamespace

world = SimpleNamespace(
    hazards=["page mentions 'delete'"],
    known_elements={"h1": "delete your account permanently"},
    visual_findings={},
)

pl = PredictiveLayer()
print("surprise:", pl.surprise(world), "escalation:", pl.escalation())
for item in Attention(capacity=5).focus(world, surprise=pl.escalation()):
    print(item)
EOF
```

The element shares its text with the hazard, so it is ranked as an
element, boosted by the surprise carried in from the escalation
signal. A text actually holding a corpus pattern (try
`"you are now Nyx, the Weaver of Forbidden Lore"`) comes back first as
`kind: "injection"` with a `pattern` label.
