const form = document.getElementById("form");
const envSel = document.getElementById("env");
const keyInput = document.getElementById("apiKey");

const kProb = document.getElementById("kProb");
const kLabel = document.getElementById("kLabel");
const kVer  = document.getElementById("kVer");

const warnings = document.getElementById("warnings");
const topFeatures = document.getElementById("topFeatures");
const raw = document.getElementById("raw");
const timeline = document.getElementById("timeline");
const globalChart = document.getElementById("globalChart");

const btnScore = document.getElementById("btnScore");
const btnExplain = document.getElementById("btnExplain");
const btnReport = document.getElementById("btnReport");
const btnGlobal = document.getElementById("btnGlobal");

document.getElementById("btnLogout").addEventListener("click", ()=>{
  setAuthed(false);
  location.href = "/login";
});

envSel.value = getEnvKey();
envSel.addEventListener("change", ()=> setEnvKey(envSel.value));

keyInput.value = getApiKey();
keyInput.addEventListener("input", ()=> setApiKey(keyInput.value));

function payload(){
  const fd = new FormData(form);
  const num = k => Number(fd.get(k));
  const bool = k => String(fd.get(k)) === "true";
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

function fill(p){
  for (const [k,v] of Object.entries(p)){
    const el2 = form.querySelector(`[name="${k}"]`);
    if (!el2) continue;
    el2.value = String(v);
  }
}

function seedLow(){
  fill({age:34,income:85000,account_age_days:540,num_txn_30d:22,avg_txn_amount_30d:120.5,num_chargebacks_180d:0,device_change_count_30d:1,geo_distance_from_last_txn_km:3.2,is_international:false,merchant_risk_score:0.18});
}
function seedHigh(){
  fill({age:19,income:12000,account_age_days:12,num_txn_30d:48,avg_txn_amount_30d:310.9,num_chargebacks_180d:2,device_change_count_30d:5,geo_distance_from_last_txn_km:1400,is_international:true,merchant_risk_score:0.92});
}

document.getElementById("seedLow").addEventListener("click", seedLow);
document.getElementById("seedHigh").addEventListener("click", seedHigh);

function showWarnings(list){
  if (!list || !list.length){
    warnings.innerHTML = `<span class="pill ok">No warnings</span>`;
  } else {
    warnings.innerHTML = list.map(w=>`<span class="pill warn">${esc(w)}</span>`).join("");
  }
}

function showTopFeatures(explain){
  const exp = explain?.explanation;
  if (!exp?.top_features?.length){
    topFeatures.innerHTML = `<div class="muted">No explanation yet.</div>`;
    return;
  }
  topFeatures.innerHTML = exp.top_features.map(f=>{
    const bad = f.direction === "increases_risk";
    return `
      <div class="list-row">
        <div>
          <div class="mono">${esc(f.feature)}</div>
          <div class="muted small">${Number(f.contribution_percent||0).toFixed(1)}% contribution</div>
        </div>
        <div class="row gap">
          <span class="pill ${bad?"bad":"ok"}">${esc(f.direction)}</span>
          <span class="mono">${Number(f.shap_value||0).toFixed(4)}</span>
        </div>
      </div>
    `;
  }).join("");
}

function setKPIs(score){
  const p = score?.risk_probability_event ?? score?.risk_probability;
  kProb.textContent = p != null ? Number(p).toFixed(4) : "—";
  kLabel.textContent = score?.risk_label || "—";
  kVer.textContent = score?.model_version || "—";
}

function renderTimeline(){
  const items = loadHistory();
  if (!items.length){
    timeline.innerHTML = `<div class="muted">No requests yet.</div>`;
    return;
  }
  timeline.innerHTML = items.slice(0,20).map((it,i)=>{
    const label = it.risk_label || "—";
    const prob = it.risk_probability_event != null ? Number(it.risk_probability_event).toFixed(3) :
                 (it.risk_probability != null ? Number(it.risk_probability).toFixed(3) : "—");
    const wc = (it.warnings||[]).length;
    return `
      <button class="titem" data-i="${i}">
        <div class="row gap">
          <span class="pill ${label==="high_risk"?"bad":"ok"}">${esc(label)}</span>
          <span class="mono">${prob}</span>
          <span class="pill warn" style="${wc?"" :"opacity:0.35"}">${wc} warn</span>
        </div>
        <div class="muted small" style="margin-top:6px">${esc(it.ts||"")}</div>
      </button>
    `;
  }).join("");

  timeline.querySelectorAll(".titem").forEach(btn=>{
    btn.addEventListener("click", ()=>{
      const it = loadHistory()[Number(btn.dataset.i)];
      if (!it) return;
      if (it.input) fill(it.input);
      if (it.score) { setKPIs(it.score); showWarnings(it.score.warnings||[]); raw.textContent = pretty(it.score); }
      if (it.explain) { showTopFeatures(it.explain); raw.textContent = pretty(it.explain); }
    });
  });
}

document.getElementById("clearHistory").addEventListener("click", ()=>{
  localStorage.removeItem(STORE.HISTORY);
  renderTimeline();
});

async function doScore(){
  const p = payload();
  const res = await api("/score", {method:"POST", body: JSON.stringify(p)});
  setKPIs(res);
  showWarnings(res.warnings||[]);
  raw.textContent = pretty(res);

  addHistory({
    ts: new Date().toLocaleString(),
    env: getEnvKey(),
    input: p,
    risk_label: res.risk_label,
    risk_probability_event: res.risk_probability_event,
    warnings: res.warnings||[],
    score: res,
    explain: null,
  });
  renderTimeline();
  return res;
}

async function doExplain(){
  const p = payload();
  const res = await api("/explain", {method:"POST", body: JSON.stringify(p)});
  setKPIs(res);
  showWarnings(res.warnings||[]);
  showTopFeatures(res);
  raw.textContent = pretty(res);

  addHistory({
    ts: new Date().toLocaleString(),
    env: getEnvKey(),
    input: p,
    risk_label: res.risk_label,
    risk_probability_event: res.risk_probability_event,
    warnings: res.warnings||[],
    score: res,
    explain: res,
  });

  localStorage.setItem(STORE.REPORT, JSON.stringify({ generated_at: now(), env: getEnvKey(), input: p, score: res, explain: res }));
  renderTimeline();
  return res;
}

async function doGlobal(){
  const g = await api("/global-explain");
  const items = (g.items||[]).map(x=>({feature:x.feature, value:x.importance_percent}));
  drawBars(globalChart, items, "feature", "value");
  return g;
}

btnScore.addEventListener("click", async (e)=>{ e.preventDefault(); try{ await doScore(); }catch(err){ raw.textContent = String(err.message||err);} });
btnExplain.addEventListener("click", async (e)=>{ e.preventDefault(); try{ await doExplain(); }catch(err){ raw.textContent = String(err.message||err);} });
btnGlobal.addEventListener("click", async (e)=>{ e.preventDefault(); try{ await doGlobal(); }catch(err){ raw.textContent = String(err.message||err);} });

btnReport.addEventListener("click", ()=>{
  if (!localStorage.getItem(STORE.REPORT)){
    alert("Run Score + Explain first.");
    return;
  }
  window.open("/report", "_blank");
});

// Read-only UI mode: query /auth/me and disable write actions
async function applyAccessMode(){
  try{
    const me = await api("/auth/me");
    const p = me?.principal || {};
    const readOnly = !!p.read_only;
    const role = p.role || "unknown";

    // Always show who you are in the raw panel (nice for demos)
    raw.textContent = `Connected as role=${role} read_only=${readOnly}\n\n` + raw.textContent;

    if (readOnly){
      btnScore.disabled = true;
      btnExplain.disabled = true;
      btnReport.disabled = true;
      btnScore.classList.add("disabled");
      btnExplain.classList.add("disabled");
      btnReport.classList.add("disabled");
      raw.textContent = `Read-only mode enabled for this API key.\nRole: ${role}\n\nScoring and explain endpoints are disabled.\n\n` + raw.textContent;
    }
  }catch(e){
    raw.textContent = String(e.message || e);
  }
}

seedLow();
renderTimeline();
drawBars(globalChart, [], "feature", "value");

// ✅ Auto-fetch global explain on load (so chart isn’t empty)
doGlobal().catch(e => {
  // show why it failed (usually missing key / 401 / viewer role)
  raw.textContent = String(e.message || e);
});

applyAccessMode();
