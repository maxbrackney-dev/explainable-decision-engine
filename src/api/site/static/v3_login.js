const btn = document.getElementById("btnLogin");
btn.addEventListener("click", (e)=>{
  e.preventDefault();
  const email = (document.getElementById("email").value || "").trim();
  const pw = (document.getElementById("pw").value || "").trim();

  // Demo-only: allow any non-empty input
  if (!email || !pw){
    alert("Enter any email + password (demo auth).");
    return;
  }
  setAuthed(true);
  location.href = "/app";
});

// If already authed, bounce to portal
if (isAuthed()) location.href = "/app";
