const mModel = document.getElementById("mModel");
const mVersion = document.getElementById("mVersion");
const mAuc = document.getElementById("mAuc");
const mBrier = document.getElementById("mBrier");
const raw = document.getElementById("raw");
const impChart = document.getElementById("impChart");
const impList = document.getElementById("impList");

function setText(elm, txt){ if (elm) elm.textContent = txt; }

async function loadAll(){
  raw.textContent = "Loading…";

  // If no key is set, guide the user clearly.
  const key = localStorage.getItem("ede_api_key") || "";
  if (!key){
    raw.textContent =
      "Missing API key.\n\nSet the API key above (try: demo_key) then click Refresh.\n\n" +
      "Your backend requires X-API-Key for /v1/* endpoints.";
    return;
  }

  try{
    const info = await api("/model-info");
    raw.textContent = pretty(info);

    setText(mModel, info.model_type || "—");
    setText(mVersion, `version: ${info.model_version || "—"}`);

    const auc = info.metrics?.test?.auc;
    const brier = info.metrics?.test?.brier;
    setText(mAuc, auc != null ? Number(auc).toFixed(4) : "—");
    setText(mBrier, brier != null ? Number(brier).toFixed(4) : "—");

    const g = await api("/global-explain");
    const items = (g.items || []).map(x => ({ feature: x.feature, value: x.importance_percent }));
    drawBars(impChart, items, "feature", "value");

    impList.innerHTML = items.slice(0,10).map(it => `
      <div class="list-row">
        <div class="mono">${esc(it.feature)}</div>
        <div class="mono">${Number(it.value||0).toFixed(1)}%</div>
      </div>
    `).join("");
  }catch(e){
    raw.textContent = String(e.message || e);
  }
}

document.getElementById("btnRefresh").addEventListener("click", (e)=>{
  e.preventDefault();
  loadAll();
});

loadAll();
