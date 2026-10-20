/* Ganglion dashboard - vanilla, no build step. */

const $ = (id) => document.getElementById(id);
let playing = false;
let playTimer = null;

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function gauge(label, value, max, cls) {
  const row = el("div", "gauge");
  row.append(el("span", "gauge-label", label));
  const track = el("div", "track");
  const fill = el("div", "fill " + (cls || ""));
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  fill.style.width = pct + "%";
  track.append(fill);
  row.append(track);
  row.append(el("span", "gauge-value", typeof value === "number" ? value.toFixed(2) : value));
  return row;
}

function kv(label, value) {
  const row = el("div", "kv");
  row.append(el("span", "k", label));
  row.append(el("span", "v", value === undefined || value === null ? "-" : String(value)));
  return row;
}

function table(headers, rows) {
  const t = el("table");
  const head = el("tr");
  headers.forEach((h) => head.append(el("th", null, h)));
  t.append(head);
  rows.forEach((cells) => {
    const tr = el("tr");
    cells.forEach((c) => tr.append(el("td", null, c)));
    t.append(tr);
  });
  return t;
}

async function api(path, body) {
  const options = body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : {};
  const res = await fetch(path, options);
  return res.json();
}

/* ------------------------------------------------------------ rendering */
function renderPage(s) {
  const host = $("page");
  clear(host);
  const page = s.page || {};
  host.append(el("div", "url", page.url || "-"));
  host.append(el("div", "title", page.title || ""));
  host.append(el("p", "text", page.text || ""));

  const targets = new Set((s.plan || []).map((step) => step.x + ":" + step.y));
  (page.elements || []).forEach((e) => {
    const row = el("div", "element" + (targets.has(e.x + ":" + e.y) ? " target" : ""));
    row.append(el("span", "tag", e.tag));
    row.append(el("span", "label", e.text));
    row.append(el("span", "coords", e.x + "," + e.y));
    host.append(row);
  });

  const hazards = (s.world || {}).hazards || [];
  if (hazards.length) {
    const box = el("div", "hazards");
    box.append(el("span", "tag", "hazards"));
    hazards.forEach((h) => box.append(el("span", "hazard", h)));
    host.append(box);
  }

  const findings = (s.world || {}).visual_findings || {};
  const names = Object.keys(findings);
  if (names.length) {
    const box = el("div", "hazards");
    box.append(el("span", "tag", "screen"));
    names.forEach((n) => box.append(el("span", findings[n] ? "ok" : "miss",
      n + (findings[n] ? " found" : " missing"))));
    host.append(box);
  }
}

function renderSignals(s) {
  const host = $("signals");
  clear(host);
  const sig = s.signals || {};
  host.append(gauge("escalation", sig.escalation || 0, 1, "red"));
  host.append(gauge("surprise", sig.surprise || 0, 1, "amber"));
  const affect = sig.affect || {};
  host.append(gauge("valence", (affect.valence || 0) + 1, 2, "green"));
  host.append(gauge("arousal", affect.arousal || 0, 1, "violet"));
  host.append(kv("firing threshold", sig.threshold));
  host.append(kv("fired / suppressed", sig.fired + " / " + sig.suppressed));
  host.append(kv("action budget / min", sig.max_calls));
  const mod = sig.modulation || {};
  host.append(kv("threshold x", mod.threshold_multiplier));
  host.append(kv("exploration x", mod.exploration_multiplier));
  host.append(kv("rate x", mod.rate_multiplier));
  const em = sig.emergency || {};
  host.append(kv("emergency stop", em.tripped ? "TRIPPED - " + (em.reason || "") : "clear"));
  const self = s.self_model || {};
  host.append(kv("cycles / errors", self.cycles_run + " / " + self.errors));
  host.append(kv("error rate", self.error_rate));
}

function renderPlan(s) {
  const host = $("plan");
  clear(host);
  host.append(kv("candidate", s.candidate));
  host.append(kv("confidence", s.confidence === null || s.confidence === undefined
    ? "-" : Number(s.confidence).toFixed(2)));
  const plan = s.plan || [];
  if (!plan.length) {
    host.append(el("p", "hint", "No plan ran this cycle."));
  } else {
    plan.forEach((step) => {
      const line = el("div", "step");
      line.append(el("span", "tag", step.type));
      if (step.x !== undefined) line.append(el("span", "label", "at " + step.x + "," + step.y));
      if (step.key !== undefined) line.append(el("span", "label", "key " + step.key));
      if (step.value !== undefined) line.append(el("span", "label", JSON.stringify(step.value)));
      host.append(line);
    });
  }
  if (s.note) host.append(el("p", "note", s.note));
}

function renderAttention(s) {
  const host = $("attention");
  clear(host);
  const focus = (s.world || {}).attention_focus || [];
  if (!focus.length) {
    host.append(el("p", "hint", "Nothing is salient."));
    return;
  }
  focus.forEach((item) => {
    const row = el("div", "focus " + (item.kind || ""));
    row.append(el("span", "tag", item.kind));
    row.append(el("span", "label", item.item));
    row.append(el("span", "score", Number(item.salience).toFixed(2)));
    if (item.pattern) row.append(el("span", "pattern", item.pattern));
    host.append(row);
  });
}

function renderLearning(s) {
  const host = $("learning");
  clear(host);
  const learn = s.learning || {};
  const standings = learn.standings || {};
  const names = Object.keys(standings);
  host.append(kv("context", learn.context));
  host.append(kv("prediction accuracy", learn.prediction_accuracy));
  if (!names.length) {
    host.append(el("p", "hint", "No candidates tried yet."));
    return;
  }
  const biases = learn.hebbian || {};
  host.append(table(
    ["candidate", "tries", "wins", "win rate", "hebbian"],
    names.map((n) => {
      const st = standings[n];
      const bias = biases[n];
      return [n, st.attempts, st.wins, Number(st.win_rate).toFixed(2),
        bias === undefined ? "-" : Number(bias).toFixed(2)];
    })
  ));
}

function renderMemory(s) {
  const host = $("memory");
  clear(host);
  const mem = s.memory || {};
  host.append(kv("episodes", mem.entries));
  const semantic = mem.semantic || {};
  const semNames = Object.keys(semantic);
  if (semNames.length) {
    host.append(el("div", "sub", "semantic"));
    semNames.forEach((n) => host.append(kv(n, JSON.stringify(semantic[n]))));
  }
  host.append(el("div", "sub", "recent"));
  const recent = mem.recent || [];
  if (!recent.length) host.append(el("p", "hint", "Nothing remembered yet."));
  recent.slice().reverse().forEach((entry) => {
    const row = el("div", "entry");
    row.append(el("span", "k", entry.key));
    row.append(el("span", "v", JSON.stringify(entry.value)));
    host.append(row);
  });
}

function renderActions(s) {
  const host = $("actions");
  clear(host);
  const actions = s.actions || [];
  if (!actions.length) {
    host.append(el("p", "hint", "Nothing acted yet."));
    return;
  }
  actions.slice().reverse().forEach((a) => {
    const row = el("div", "entry");
    row.append(el("span", "k", a.type));
    row.append(el("span", "v", a.target || a.text || a.key ||
      (a.amount !== undefined ? "amount " + a.amount : "")));
    host.append(row);
  });
}

function renderWorkspace(s) {
  const host = $("workspace");
  clear(host);
  const ws = s.workspace || {};
  const keys = Object.keys(ws);
  if (!keys.length) {
    host.append(el("p", "hint", "Nothing broadcast yet."));
    return;
  }
  keys.forEach((k) => {
    if (k === "attention") return;
    host.append(kv(k, typeof ws[k] === "object" ? JSON.stringify(ws[k]) : ws[k]));
  });
}

function renderAudit(s) {
  const host = $("audit");
  clear(host);
  const entries = (s.audit || []).slice().reverse();
  if (!entries.length) {
    host.append(el("p", "hint", "Nothing logged yet."));
    return;
  }
  entries.forEach((entry) => {
    const row = el("div", "audit " + (entry.event || ""));
    row.append(el("span", "event", entry.event));
    const detail = entry.detail && Object.keys(entry.detail).length
      ? JSON.stringify(entry.detail)
      : "";
    row.append(el("span", "detail", detail));
    host.append(row);
  });
}

function render(s) {
  $("cycle").textContent = s.cycle;
  $("outcome").textContent = s.outcome || "";
  $("outcome").className = "outcome" + (/blocked|held|skipped|stop/i.test(s.outcome || "") ? " warn" : "");
  $("scenario-note").textContent = (s.scenario && s.scenario.description) || "";
  renderPage(s);
  renderSignals(s);
  renderPlan(s);
  renderAttention(s);
  renderLearning(s);
  renderMemory(s);
  renderWorkspace(s);
  renderActions(s);
  renderAudit(s);
}

/* -------------------------------------------------------------- actions */
async function step() {
  render(await api("/api/step", {}));
}

async function reset() {
  const scenario = $("scenario").value;
  render(await api("/api/reset", { scenario: scenario }));
}

async function loadScenarios() {
  const data = await api("/api/scenarios");
  const select = $("scenario");
  clear(select);
  data.scenarios.forEach((s) => {
    const opt = el("option", null, s.name);
    opt.value = s.id;
    select.append(opt);
  });
}

function stopPlaying() {
  playing = false;
  clearInterval(playTimer);
  $("play").textContent = "Play";
}

async function play() {
  if (playing) {
    stopPlaying();
    return;
  }
  playing = true;
  $("play").textContent = "Pause";
  playTimer = setInterval(async () => {
    if (!playing) return;
    render(await api("/api/step", {}));
  }, 700);
}

function parseElements(text) {
  return text.split("\n").map((line) => line.trim()).filter(Boolean).map((line) => {
    const [tag, ...rest] = line.split("|");
    if (rest.length) return [tag.trim(), rest.join("|").trim()];
    return ["button", tag.trim()];
  });
}

$("step").addEventListener("click", step);
$("run").addEventListener("click", async () => {
  stopPlaying();
  for (let i = 0; i < 5; i++) render(await api("/api/step", {}));
});
$("play").addEventListener("click", play);
$("reset").addEventListener("click", () => { stopPlaying(); reset(); });
$("scenario").addEventListener("change", () => { stopPlaying(); reset(); });
$("habituation").addEventListener("change", async (e) => {
  render(await api("/api/config", { habituation: e.target.checked }));
});
$("emergency").addEventListener("click", async () => {
  const tripped = $("emergency").classList.contains("tripped");
  render(await api("/api/config", { emergency: !tripped }));
  $("emergency").classList.toggle("tripped", !tripped);
  $("emergency").textContent = tripped ? "Trip stop" : "Clear stop";
});
$("custom-load").addEventListener("click", async () => {
  stopPlaying();
  render(await api("/api/reset", {
    custom: {
      text: $("custom-text").value,
      elements: parseElements($("custom-elements").value),
    },
  }));
});

loadScenarios().then(reset);
