const STORAGE = {
  ENV: "ede_env",
  API_KEY: "ede_api_key",
  HISTORY: "ede_history",
  REPORT: "ede_last_report",
};

const ENVIRONMENTS = {
  dev: { label: "DEV", base: "/v1", hint: "Same-origin API (local dev)" },
  stage: { label: "STAGE", base: "/v1", hint: "Demo selector (wire to stage later)" },
  prod: { label: "PROD", base: "/v1", hint: "Demo selector (wire to prod later)" },
};

const el = (id) => document.getElementById(id);

const state = {
  lastScore: null,
  lastExplain: null,
  lastGlobal: null,
};

function pretty(obj) { return JSON.stringify(obj, null, 2); }
function nowISO() { return new Date().toISOString(); }

function getEnvKey() { return localStorage.getItem(STORAGE.ENV) || "dev"; }
function setEnvKey(v) { localStorage.setItem(STORAGE.ENV, v); }
function getApiKey() { return localStorage.getItem(STORAGE.API_KEY) || ""; }
function setApiKey(v) { localStorage.setItem(STORAGE.API_KEY, v); }

function apiBase() {
  const env = ENVIRONMENTS[getEnvKey()] || ENVIRONMENTS.dev;
  return env.base;
}

function setEnvBanner() {
  const env = ENVIRONMENTS[getEnvKey()] || ENVIRONMENTS.dev;
  const banner = el("envBanner");
  banner.innerHTML = `
    <span class="pill pill-ok">${env.label}</span>
    <span class="muted small">${env.hint}</span>
  `;
}

function formToPayload() {
  const form = el("form");
  const fd = new FormData(form);

  const num = (k) => Number(fd.get(k));
  const bool = (k) => String(fd.get(k)) === "true";

  return {
    age: Math.trunc(num("age")),
    income: num("income"),
    account_age_days: Math.trunc(num("account_age_days")),
    num_txn_30d: Math.trunc(num("num_txn_30d")),
    avg_txn_amount_30d: num("avg_txn_amount_30d"),
    num_chargebacks_180d: Math.trunc(num("num_chargebacks_180d")),
    device_change_count_30d: Math.trunc(num("device_change_count_30d")),
    geo_distance_from_last_txn_km: num("geo_distance_from_last_txn_km"),
    is_international: bool("is_international"),
    merchant_risk_score: num("merchant_risk_score"),
  };
}

function fill(payload) {
  const form = el("form");
  for (const [k, v] of Object.entries(payload)) {
    const input = form.querySelector(`[name="${k}"]`);
    if (!input) continue;
    if (input.tagName === "SELECT") input.value = String(v);
    else input.value = String(v);
  }
}

function seedLow() {
  fill({
    age: 34,
    income: 85000,
    account_age_days: 540,
    num_txn_30d: 22,
    avg_txn_amount_30d: 120.5,
    num_chargebacks_180d: 0,
    device_change_count_30d: 1,
    geo_distance_from_last_txn_km: 3.2,
    is_international: false,
    merchant_risk_score: 0.18,
  });
}

function seedHigh() {
  fill({
    age: 19,
    income: 12000,
    account_age_days: 12,
    num_txn_30d: 48,
    avg_txn_amount_30d: 310.9,
    num_chargebacks_180d: 2,
    device_change_count_30d: 5,
    geo_distance_from_last_txn_km: 1400,
    is_international: true,
    merchant_risk_score: 0.92,
  });
}

async function api(path, options = {}) {
  const base = apiBase();
  const key = getApiKey();

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (key) headers["X-API-Key"] = key;

  const res = await fetch(`${base}${path}`, { ...options, headers });
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }

  if (!res.ok) {
    const msg = typeof data === "object" ? pretty(data) : String(data);
    throw new Error(`HTTP ${res.status}: ${msg}`);
  }
  return data;
}

function setText(id, text) { el(id).textContent = text; }

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderScore(score) {
  state.lastScore = score;

  setText("kpi-prob", score?.risk_probability != null ? Number(score.risk_probability).toFixed(4) : "—");
  setText("kpi-label", score?.risk_label ?? "—");
  setText("kpi-version", score?.model_version ?? "—");

  const warnings = score?.warnings ?? [];
  if (!warnings.length) {
    el("warnings").innerHTML = `<span class="pill pill-ok">No warnings</span>`;
  } else {
    el("warnings").innerHTML = warnings.map(w => `<span class="pill pill-warn">${escapeHtml(w)}</span>`).join("");
  }

  setText("raw", pretty(score));
}

function renderExplain(explain) {
  state.lastExplain = explain;

  const exp = explain?.explanation;
  if (!exp?.top_features?.length) {
    el("explain-list").innerHTML = `<div class="muted">No explanation returned</div>`;
    return;
  }

  const rows = exp.top_features.map(f => {
    const dirClass = f.direction === "increases_risk" ? "pill-bad" : "pill-ok";
    const pct = (f.contribution_percent ?? 0).toFixed(1);
    const val = (f.shap_value ?? 0).toFixed(4);

    return `
      <div class="list-row">
        <div class="list-left">
          <div class="mono">${escapeHtml(f.feature)}</div>
          <div class="muted small">${pct}% contribution</div>
        </div>
        <div class="list-right">
          <span class="pill ${dirClass}">${escapeHtml(f.direction)}</span>
          <span class="mono">${val}</span>
        </div>
      </div>
    `;
  }).join("");

  el("explain-list").innerHTML = rows;
  setText("raw", pretty(explain));
}

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(STORAGE.HISTORY) || "[]"); }
  catch { return []; }
}

function saveHistory(items) {
  localStorage.setItem(STORAGE.HISTORY, JSON.stringify(items.slice(0, 50)));
}

function addHistoryEntry(entry) {
  const items = loadHistory();
  items.unshift(entry);
  saveHistory(items);
  renderHistory();
}

function clearHistory() {
  localStorage.removeItem(STORAGE.HISTORY);
  renderHistory();
}

function renderHistory() {
  const wrap = el("history");
  const items = loadHistory();
  if (!items.length) {
    wrap.innerHTML = `<div class="muted">No requests yet.</div>`;
    return;
  }

  wrap.innerHTML = items.map((it, idx) => {
    const label = it.risk_label || "—";
    const prob = it.risk_probability != null ? Number(it.risk_probability).toFixed(3) : "—";
    const env = it.env || "dev";
    const ts = it.ts || "";
    const warnCount = (it.warnings || []).length;

    return `
      <button class="timeline-item" data-idx="${idx}">
        <div class="timeline-top">
          <span class="pill ${label === "high_risk" ? "pill-bad" : "pill-ok"}">${escapeHtml(label)}</span>
          <span class="mono">${prob}</span>
          <span class="pill pill-warn" style="${warnCount ? "" : "opacity:0.35"}">${warnCount} warn</span>
          <span class="pill">${escapeHtml(env.toUpperCase())}</span>
        </div>
        <div class="timeline-bottom">
          <span class="muted small">${escapeHtml(ts)}</span>
          <span class="muted small">Click to restore</span>
        </div>
      </button>
    `;
  }).join("");

  wrap.querySelectorAll(".timeline-item").forEach(btn => {
    btn.addEventListener("click", () => {
      const idx = Number(btn.dataset.idx);
      const item = loadHistory()[idx];
      if (!item) return;

      if (item.input) fill(item.input);
      if (item.score) renderScore(item.score);
      if (item.explain) renderExplain(item.explain);
      if (item.global) { state.lastGlobal = item.global; drawGlobalChart(item.global); }

      setText("raw", pretty(item.explain || item.score || item));
    });
  });
}

function openReport() {
  if (!state.lastExplain && !state.lastScore) {
    alert("Run Score or Explain first.");
    return;
  }

  const payload = formToPayload();
  const env = getEnvKey();

  const report = {
    env,
    generated_at: nowISO(),
    input: payload,
    score: state.lastScore,
    explain: state.lastExplain,
  };

  localStorage.setItem(STORAGE.REPORT, JSON.stringify(report));
  window.open("/report", "_blank");
}

async function doScore() {
  const payload = formToPayload();
  const data = await api("/score", { method: "POST", body: JSON.stringify(payload) });
  renderScore(data);

  addHistoryEntry({
    ts: new Date().toLocaleString(),
    env: getEnvKey(),
    input: payload,
    risk_label: data.risk_label,
    risk_probability: data.risk_probability,
    warnings: data.warnings || [],
    score: data,
    explain: null,
    global: state.lastGlobal || null,
  });

  return data;
}

async function doExplain() {
  const payload = formToPayload();
  const data = await api("/explain", { method: "POST", body: JSON.stringify(payload) });
  renderScore(data);
  renderExplain(data);

  addHistoryEntry({
    ts: new Date().toLocaleString(),
    env: getEnvKey(),
    input: payload,
    risk_label: data.risk_label,
    risk_probability: data.risk_probability,
    warnings: data.warnings || [],
    score: {
      risk_probability: data.risk_probability,
      risk_label: data.risk_label,
      model_version: data.model_version,
      warnings: data.warnings,
    },
    explain: data,
    global: state.lastGlobal || null,
  });

  return data;
}

async function doGlobal() {
  const data = await api("/global-explain");
  state.lastGlobal = data;
  drawGlobalChart(data);
  return data;
}

function copyToClipboard(text) { navigator.clipboard.writeText(text); }

function drawGlobalChart(global) {
  const canvas = el("global-chart");
  const ctx = canvas.getContext("2d");

  const items = global?.items ?? [];
  const top = items.slice(0, 8);

  const w = canvas.width = canvas.clientWidth * window.devicePixelRatio;
  const h = canvas.height = canvas.clientHeight * window.devicePixelRatio;
  ctx.clearRect(0, 0, w, h);

  if (!top.length) {
    ctx.fillStyle = "rgba(255,255,255,0.6)";
    ctx.font = `${14 * window.devicePixelRatio}px system-ui`;
    ctx.fillText("No global data yet. Click Global Explain.", 20, 40);
    return;
  }

  const pad = 18 * window.devicePixelRatio;
  const barH = 16 * window.devicePixelRatio;
  const gap = 10 * window.devicePixelRatio;
  const max = Math.max(...top.map(x => x.importance_percent ?? 0)) || 1;

  ctx.font = `${12 * window.devicePixelRatio}px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`;
  ctx.textBaseline = "middle";

  top.forEach((d, i) => {
    const y = pad + i * (barH + gap);
    const pct = d.importance_percent ?? 0;
    const barW = ((w - pad * 2) * (pct / max));

    ctx.fillStyle = "rgba(255,255,255,0.07)";
    ctx.fillRect(pad, y, w - pad * 2, barH);

    ctx.fillStyle = "rgba(37,99,235,0.85)";
    ctx.fillRect(pad, y, barW, barH);

    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.fillText(`${d.feature}`, pad, y + barH / 2);

    const txt = `${pct.toFixed(1)}%`;
    const tw = ctx.measureText(txt).width;
    ctx.fillText(txt, w - pad - tw, y + barH / 2);
  });
}

function bannerError(err) { el("raw").textContent = String(err?.message ?? err); }

function hook() {
  el("env").value = getEnvKey();
  el("env").addEventListener("change", () => { setEnvKey(el("env").value); setEnvBanner(); });

  el("apiKey").value = getApiKey();
  el("apiKey").addEventListener("input", () => setApiKey(el("apiKey").value));

  setEnvBanner();

  el("btn-seed-low").addEventListener("click", seedLow);
  el("btn-seed-high").addEventListener("click", seedHigh);

  el("btn-run").addEventListener("click", async () => { try { await doExplain(); } catch (e) { bannerError(e); } });

  el("btn-score").addEventListener("click", async (ev) => { ev.preventDefault(); try { await doScore(); } catch (e) { bannerError(e); } });
  el("btn-explain").addEventListener("click", async (ev) => { ev.preventDefault(); try { await doExplain(); } catch (e) { bannerError(e); } });
  el("btn-global").addEventListener("click", async (ev) => { ev.preventDefault(); try { await doGlobal(); } catch (e) { bannerError(e); } });

  el("btn-clear-history").addEventListener("click", (ev) => { ev.preventDefault(); clearHistory(); });

  el("btn-copy-score").addEventListener("click", () => { if (!state.lastScore) return; copyToClipboard(pretty(state.lastScore)); });
  el("btn-copy-explain").addEventListener("click", () => { if (!state.lastExplain) return; copyToClipboard(pretty(state.lastExplain)); });

  el("btn-report").addEventListener("click", () => openReport());

  window.addEventListener("resize", () => drawGlobalChart(state.lastGlobal));

  seedLow();
  drawGlobalChart(null);
  renderHistory();
}

hook();
