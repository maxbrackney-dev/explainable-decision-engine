const tbody = document.getElementById("tbody");
const filter = document.getElementById("filter");
const labelFilter = document.getElementById("labelFilter");

function rows(){
  const items = loadHistory();
  const q = (filter.value||"").toLowerCase().trim();
  const lab = labelFilter.value;

  return items.filter(it=>{
    if (lab && it.risk_label !== lab) return false;
    if (!q) return true;

    const blob = JSON.stringify(it).toLowerCase();
    return blob.includes(q);
  });
}

function render(){
  const items = rows();
  if (!items.length){
    tbody.innerHTML = `<tr><td colspan="6" class="muted">No matching requests.</td></tr>`;
    return;
  }

  tbody.innerHTML = items.slice(0,200).map((it,i)=>{
    const label = it.risk_label || "—";
    const prob = it.risk_probability != null ? Number(it.risk_probability).toFixed(4) : "—";
    const env = (it.env||"dev").toUpperCase();
    const warns = (it.warnings||[]).length;

    return `
      <tr>
        <td>${esc(it.ts||"")}</td>
        <td><span class="pill">${esc(env)}</span></td>
        <td><span class="pill ${label==="high_risk"?"bad":"ok"}">${esc(label)}</span></td>
        <td class="mono">${prob}</td>
        <td>${warns ? `<span class="pill warn">${warns} warnings</span>` : `<span class="pill ok">0</span>`}</td>
        <td>
          <a class="btn ghost sm" href="/app" data-load="${i}">Load</a>
        </td>
      </tr>
    `;
  }).join("");

  // wire "Load"
  tbody.querySelectorAll("[data-load]").forEach(a=>{
    a.addEventListener("click", ()=>{
      const idx = Number(a.dataset.load);
      const it2 = items[idx];
      localStorage.setItem(STORE.REPORT, JSON.stringify({ generated_at: now(), env: it2.env||"dev", input: it2.input, score: it2.score||it2, explain: it2.explain||null }));
      localStorage.setItem("ede_restore", JSON.stringify(it2));
    });
  });
}

document.getElementById("btnClear").addEventListener("click", ()=>{
  if (!confirm("Clear local audit history?")) return;
  localStorage.removeItem(STORE.HISTORY);
  render();
});

document.getElementById("btnExport").addEventListener("click", ()=>{
  const items = rows();
  const out = [["time","env","label","prob","warnings","input_json"]];
  items.forEach(it=>{
    out.push([
      it.ts||"",
      it.env||"",
      it.risk_label||"",
      it.risk_probability ?? "",
      (it.warnings||[]).join("; "),
      JSON.stringify(it.input||{})
    ]);
  });
  downloadCSV("decision_audit.csv", out);
});

filter.addEventListener("input", render);
labelFilter.addEventListener("change", render);

render();
