const STORAGE_REPORT = "ede_last_report";

function pretty(obj) { return JSON.stringify(obj, null, 2); }

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function pill(type, text) {
  const cls =
    type === "ok" ? "pill pill-ok" :
    type === "warn" ? "pill pill-warn" :
    type === "bad" ? "pill pill-bad" :
    "pill";
  return `<span class="${cls}">${escapeHtml(text)}</span>`;
}

function render() {
  const raw = localStorage.getItem(STORAGE_REPORT);
  if (!raw) {
    document.body.innerHTML = `<div style="padding:24px;color:white">No report data found. Go to /app and run Score + Explain first.</div>`;
    return;
  }

  const report = JSON.parse(raw);
  const score = report.score || {};
  const explain = report.explain || {};
  const input = report.input || {};
  const env = report.env || "dev";

  document.getElementById("r-prob").textContent = score.risk_probability != null ? Number(score.risk_probability).toFixed(4) : "—";
  document.getElementById("r-label").textContent = score.risk_label || "—";
  document.getElementById("r-version").textContent = score.model_version || "—";
  document.getElementById("r-time").textContent = report.generated_at || "—";
  document.getElementById("r-env").textContent = env.toUpperCase();

  const warnings = (score.warnings || []);
  document.getElementById("r-warnings").innerHTML = warnings.length ? warnings.map(w => pill("warn", w)).join("") : pill("ok", "No warnings");

  document.getElementById("r-input").textContent = pretty(input);
  document.getElementById("r-raw").textContent = pretty(explain || score);

  const exp = explain.explanation;
  if (exp && exp.top_features && exp.top_features.length) {
    const rows = exp.top_features.map(f => {
      const dir = f.direction || "";
      const dirType = dir === "increases_risk" ? "bad" : "ok";
      const pct = (f.contribution_percent ?? 0).toFixed(1);
      const val = (f.shap_value ?? 0).toFixed(4);

      return `
        <div class="report-row">
          <div>
            <div class="mono">${escapeHtml(f.feature)}</div>
            <div class="muted small">${pct}% contribution</div>
          </div>
          <div class="row gap">
            ${pill(dirType, dir)}
            <span class="mono">${val}</span>
          </div>
        </div>
      `;
    }).join("");
    document.getElementById("r-explain").innerHTML = rows;
  } else {
    document.getElementById("r-explain").innerHTML = `<div class="muted">No explanation data found.</div>`;
  }

  document.getElementById("btn-print").addEventListener("click", () => window.print());
}

render();
