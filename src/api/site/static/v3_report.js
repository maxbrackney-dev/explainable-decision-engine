const pProb = document.getElementById("pProb");
const pLabel = document.getElementById("pLabel");
const pVer = document.getElementById("pVer");
const pWarn = document.getElementById("pWarn");
const pInput = document.getElementById("pInput");
const pTop = document.getElementById("pTop");
const pRaw = document.getElementById("pRaw");

document.getElementById("btnPrint").addEventListener("click", ()=> window.print());

const raw = localStorage.getItem(STORE.REPORT);
if (!raw){
  pRaw.textContent = "No report data found. Go to /app and run Score + Explain first.";
} else {
  const report = JSON.parse(raw);
  const score = report.score || {};
  const explain = report.explain || {};
  const input = report.input || {};

  pProb.textContent = score.risk_probability != null ? Number(score.risk_probability).toFixed(4) : "—";
  pLabel.textContent = score.risk_label || "—";
  pVer.textContent = score.model_version || "—";

  const ws = score.warnings || [];
  pWarn.innerHTML = ws.length ? ws.map(w=>`<span class="pill warn">${esc(w)}</span>`).join("") : `<span class="pill ok">No warnings</span>`;

  pInput.textContent = pretty(input);
  pRaw.textContent = pretty(explain || score);

  const exp = explain.explanation;
  if (exp?.top_features?.length){
    pTop.innerHTML = exp.top_features.map(f=>{
      const bad = f.direction === "increases_risk";
      return `
        <div class="list-row">
          <div>
            <div class="mono">${esc(f.feature)}</div>
            <div class="muted small">${Number(f.contribution_percent||0).toFixed(1)}%</div>
          </div>
          <div class="row gap">
            <span class="pill ${bad?"bad":"ok"}">${esc(f.direction)}</span>
            <span class="mono">${Number(f.shap_value||0).toFixed(4)}</span>
          </div>
        </div>
      `;
    }).join("");
  } else {
    pTop.innerHTML = `<div class="muted">No explain data found.</div>`;
  }
}
