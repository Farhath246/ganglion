# Ganglion

Ganglion started out as a modular, governed automation bot whose pieces
mapped onto layers of the nervous system, from a single signal crossing
a synapse up to one coordinated system making a decision (named after
the biological ganglion: a cluster of nerve cell bodies acting as a
local processing hub).

**This folder is no longer that bot.** Most of the original modules
were removed at some point; what survives is the standalone
"brain-function" layer — the learning and monitoring pieces — plus the
jailbreak-hardening work that grew out of studying the `Jailbreaks/`
corpus. This README describes what is actually here now, not what the
module names once implied.

## What's actually here

| File | What it is | Depends on | Status |
|---|---|---|---|
| `predictive_perception.py` | `PredictiveLayer` — one-step "expected vs. actual" surprise score, plus a session-level hazard-escalation signal | any object with `.hazards` | works standalone |
| `attention.py` | `Attention` — salience-ranked focus, and screening for the manipulation patterns documented in `Jailbreaks/` | object with `.hazards`, `.known_elements`, `.visual_findings` | works standalone |
| `affect.py` | `Affect` — running valence/arousal state that emits caution multipliers | nothing | works standalone |
| `forward_model.py` | `ForwardModel` — predict an action's outcome, compare after | object with `.hazards` | works standalone |
| `hebbian.py` | `HebbianAssociator` — contextual co-occurrence learning, persisted to a JSON file | object with `.hazards`, `.known_elements` (+ candidate names) | works standalone |
| `workspace.py` | `GlobalWorkspace` — per-cycle shared blackboard of salient signals | nothing | works standalone |
| `replay.py` | `ReplayConsolidator` — re-feeds logged past outcomes into basal-ganglia learning | `memory.history` entries and `basal_ganglia.reward()` from the *removed* Brain/Memory/BasalGanglia interfaces | needs the removed interfaces |
| `brain.py` | the full-cycle integration (perceive → … → audit) | ~15 modules that are no longer in this folder | **stale — won't even import** |
| `test_ganglion.py` | behavioral spec of that full stack | all of the above | **stale — won't run** |

Everything that works standalone is stdlib-only (`re`, `json`,
`random`, `os`). There is no `requirements.txt`, nothing to install,
and no browser, display, or network needed.

## The world-model duck type

Several modules were written against the old `WorldModel` object, which
is gone. What they actually touch is just three attributes, so any
object with this shape works:

- `hazards` — `list[str]`: phrases the page (or another sensor) flagged as risky
- `known_elements` — `dict[tag, str]`: visible DOM elements and their text
- `visual_findings` — `dict[name, (x, y) | None]`: where each named template image was (or wasn't) found on screen

`Attention.focus()` returns the ranked list; whoever calls it decides
where to store it (the old Brain wrote it to
`world_model.attention_focus`).

## The modules

### Predictive perception

Real perception is predictive: the brain guesses what it's about to
sense and processes mainly the *error*. `PredictiveLayer` does a
one-step-back version — honestly scoped, no hierarchy, no generative
model. It also tracks **escalation**: how many cycles in a row the
world model flagged hazards, normalized 0..1. That signal comes
directly from the corpus (see the hardening section below).

```python
from predictive_perception import PredictiveLayer

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
from attention import Attention

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
from affect import Affect

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
from forward_model import ForwardModel

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
from hebbian import HebbianAssociator

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
from workspace import GlobalWorkspace

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
calls `basal_ganglia.reward(name, success)` — so it only works against
the full Brain/Memory/BasalGanglia stack from before the removal.

```python
from replay import ReplayConsolidator

n = ReplayConsolidator(sample_size=5).run(memory, basal_ganglia)  # how many were replayed
```

## Jailbreak hardening — the corpus connection

The `Jailbreaks/` folder is a collected corpus of real jailbreak
prompts and a public CTF writeup. Its patterns are baked directly into
the surviving modules:

| Module | Signal | Where it came from |
|---|---|---|
| `attention.py` | identity / mode hijack: "you are now", "from now on", "developer/god/rebel mode" | `identity_crisis` ("You are now 'Nyx, the Weaver of Forbidden Lore'") and similar persona rewrites across the corpus |
| `attention.py` | forged config blocks and dev-mode tokens: `<interaction-config>`, `<thinking-config>`, `<courtroom-information-config>`, `developer_mode_rules(...)`, `[SYSTEM]`, `Applied-Settings-Setup` | `gpt-5/gpt-5-non-thinking`, `gemini/gemini2.5pro`, `universals/courtroom` |
| `attention.py` | forged chat-template tokens: `<\|SYSTEM\|>` | generic template-injection style seen across the corpus |
| `attention.py` | refusal suppression: pre-declared "blocked strings", "don't deny" rule lists | `universals/`, `perplexity/personalization_injection.md` |
| `attention.py` | encoded payloads: long base64 runs, mathematical-bold unicode runs | base64-wrapped harmful asks in `universals/`, plus the acrostic/emoji attempts documented in the NeMo writeup |
| `predictive_perception.py` | `escalation()` — session-level hazard streak | `Jailbreaks/research/nvdia-nemo-guardrails-bypass/writeup.md`: the successful multi-turn bypass carried zero adversarial signal in any single turn; what it left behind was intent that escalated with hazards persisting across consecutive turns |

The escalation signal is the design lesson from that writeup: per-turn
evaluation is structurally blind to slow, multi-turn attacks, so the
layer remembers what no single turn reveals.

## What's gone, and what's stale

Every other file the original README pointed at has been removed from
this folder: `perception.py`, `vision.py`, `neuron.py`,
`world_model.py`, `memory.py`, `self_model.py`, `safety.py`,
`safety_governor.py`, `audit_log.py`, `action.py`, `sandbox.py`,
`reasoning.py`, `operator_interface.py`, `mission_manager.py`,
`basal_ganglia.py`, `hemispheres.py`, `habituation.py`,
`language.py`, `working_memory.py`, `meninges.py`, `reflex.py`,
`homeostasis.py`, `maintenance.py`, `main.py`, and the
requirements files.

Two files survived the removal but reference it anyway:

- **`brain.py`** — imports fifteen of the removed modules and will not
  import until they return. Kept as the integration *blueprint*: its
  docstring spells out the full governed cycle (emergency stop →
  maintenance/replay → homeostasis → affect → perceive → world model →
  habituation → surprise → attention → gate → decide → lookahead →
  govern → forward-model → act → reward → remember → note →
  workspace → audit), which is the map for rewiring the surviving
  modules if the removed ones are restored.
- **`test_ganglion.py`** — same story: the behavioral spec of the full
  stack, currently unrunnable. **There is no runnable test suite in
  this folder right now.**

If those modules come back, this README should be updated again to
rejoin the full-bot documentation with the module table above.

## Smoke-testing the survivors

```bash
python3 - <<'EOF'
from affect import Affect
from workspace import GlobalWorkspace

a = Affect()
a.observe(success=True)
print(a.status(), a.modulation())

ws = GlobalWorkspace()
ws.broadcast(plan_size=1)
print("plan_size:", ws.get("plan_size"))
EOF
```

For the modules that duck-type against a world model, hand them any
object with `.hazards`, `.known_elements`, and `.visual_findings` —
for example:

```bash
python3 - <<'EOF'
from attention import Attention
from predictive_perception import PredictiveLayer
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
