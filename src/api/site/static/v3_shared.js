const STORE = {
  THEME: "ede_theme",
  AUTH: "ede_authed",
  ENV: "ede_env",
  KEY: "ede_api_key",
  HISTORY: "ede_history",
  REPORT: "ede_last_report",
};

const ENV = {
  dev:  { label: "DEV",  base: "/v1", hint: "Same-origin API" },
  stage:{ label: "STAGE",base: "/v1", hint: "Demo selector (wire later)" },
  prod: { label: "PROD", base: "/v1", hint: "Demo selector (wire later)" },
};

function $(sel){ return document.querySelector(sel); }
function $all(sel){ return Array.from(document.querySelectorAll(sel)); }
function pretty(x){ return JSON.stringify(x, null, 2); }
function now(){ return new Date().toISOString(); }
function esc(s){ return String(s).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;"); }

function getTheme(){ return localStorage.getItem(STORE.THEME) || "dark"; }
function setTheme(t){ localStorage.setItem(STORE.THEME, t); applyTheme(); }
function applyTheme(){
  const t = getTheme();
  document.documentElement.setAttribute("data-theme", t);
}
function toggleTheme(){ setTheme(getTheme()==="dark" ? "light" : "dark"); }

function isAuthed(){ return localStorage.getItem(STORE.AUTH) === "1"; }
function setAuthed(v){ localStorage.setItem(STORE.AUTH, v ? "1" : "0"); }

function requireAuth(){
  const path = location.pathname;
  if (path === "/" || path === "/login") return;
  if (!isAuthed()) location.href = "/login";
}

function getEnvKey(){ return localStorage.getItem(STORE.ENV) || "dev"; }
function setEnvKey(v){ localStorage.setItem(STORE.ENV, v); }

function getApiKey(){ return localStorage.getItem(STORE.KEY) || ""; }
function setApiKey(v){ localStorage.setItem(STORE.KEY, v || ""); }

function apiBase(){
  const e = ENV[getEnvKey()] || ENV.dev;
  return e.base;
}

/**
 * Shared wiring for any page that has:
 *  - #env (select)
 *  - #apiKey (input)
 *  - #btnSaveKey (button)
 *  - #keyStatus (status text)
 */
function wireConnectionControls(){
  const envSel = document.getElementById("env");
  const apiKeyInput = document.getElementById("apiKey");
  const saveBtn = document.getElementById("btnSaveKey");
  const status = document.getElementById("keyStatus");

  if (envSel){
    envSel.value = getEnvKey();
    envSel.addEventListener("change", ()=> setEnvKey(envSel.value));
  }
  if (apiKeyInput){
    apiKeyInput.value = getApiKey();
    apiKeyInput.addEventListener("input", ()=> setApiKey(apiKeyInput.value));
  }
  if (saveBtn){
    saveBtn.addEventListener("click", (e)=>{
      e.preventDefault();
      if (!apiKeyInput) return;
      setApiKey(apiKeyInput.value);
      updateKeyStatus();
      // small UX: attempt a quick auth check
      pingAuth().catch(()=>{});
    });
  }

  function updateKeyStatus(){
    if (!status) return;
    const k = getApiKey();
    if (!k){
      status.textContent = "Not connected";
      status.className = "hint";
      return;
    }
    status.textContent = `Connected (****${k.slice(-4)})`;
    status.className = "hint";
  }

  updateKeyStatus();
}

async function pingAuth(){
  // Try a protected endpoint to confirm the key is accepted
  try{
    await api("/model-info");
  }catch(e){
    // ignore; will show in page-specific error panes
  }
}

async function api(path, opts={}){
  const key = getApiKey();
  const headers = { "Content-Type":"application/json", ...(opts.headers||{}) };
  if (key) headers["X-API-Key"] = key;

  const res = await fetch(`${apiBase()}${path}`, { ...opts, headers });
  const text = await res.text();

  let data;
  try{ data = JSON.parse(text); } catch { data = text; }

  if (!res.ok){
    // bubble a readable error
    const msg = (typeof data === "object") ? pretty(data) : String(data);
    throw new Error(`HTTP ${res.status}: ${msg}`);
  }
  return data;
}

function loadHistory(){
  try{ return JSON.parse(localStorage.getItem(STORE.HISTORY)||"[]"); }
  catch{ return []; }
}
function saveHistory(items){ localStorage.setItem(STORE.HISTORY, JSON.stringify(items.slice(0,100))); }
function addHistory(entry){
  const items = loadHistory();
  items.unshift(entry);
  saveHistory(items);
}

function downloadCSV(filename, rows){
  const csv = rows.map(r => r.map(v => `"${String(v ?? "").replaceAll('"','""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], {type:"text/csv;charset=utf-8;"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

function drawBars(canvas, items, keyLabel, keyValue){
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.width = canvas.clientWidth * dpr;
  const h = canvas.height = canvas.clientHeight * dpr;
  ctx.clearRect(0,0,w,h);

  if (!items || !items.length){
    ctx.fillStyle = "rgba(255,255,255,0.6)";
    ctx.font = `${14*dpr}px system-ui`;
    ctx.fillText("No data yet.", 20*dpr, 40*dpr);
    return;
  }

  const top = items.slice(0, 10);
  const pad = 16*dpr;
  const barH = 16*dpr;
  const gap = 10*dpr;
  const max = Math.max(...top.map(x => x[keyValue]||0)) || 1;

  ctx.font = `${12*dpr}px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`;
  ctx.textBaseline = "middle";

  top.forEach((it,i)=>{
    const y = pad + i*(barH+gap);
    const v = it[keyValue] || 0;
    const bw = (w - pad*2) * (v/max);

    ctx.fillStyle = "rgba(255,255,255,0.07)";
    ctx.fillRect(pad, y, w-pad*2, barH);

    ctx.fillStyle = "rgba(37,99,235,0.85)";
    ctx.fillRect(pad, y, bw, barH);

    ctx.fillStyle = "rgba(255,255,255,0.88)";
    ctx.fillText(String(it[keyLabel]), pad, y + barH/2);

    const txt = (typeof v === "number" ? v.toFixed(1) : String(v));
    const tw = ctx.measureText(txt).width;
    ctx.fillText(txt, w - pad - tw, y + barH/2);
  });
}

applyTheme();
$all("[data-theme-toggle]").forEach(b => b.addEventListener("click", toggleTheme));

requireAuth();
wireConnectionControls();

const logoutBtn = document.getElementById("btnLogout");
if (logoutBtn){
  logoutBtn.addEventListener("click", ()=>{
    setAuthed(false);
    location.href = "/login";
  });
}
