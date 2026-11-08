ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>ManaTee Admin</title>
<style>
  :root { color-scheme: dark; }
  body { font-family: ui-monospace, Menlo, Consolas, monospace; background:#0d1117; color:#c9d1d9; max-width: 980px; margin: 2em auto; padding: 0 1em; }
  h1, h2 { color:#58a6ff; border-bottom: 1px solid #30363d; padding-bottom: .3em; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 1em; }
  th, td { border: 1px solid #30363d; padding: .45em .6em; text-align: left; font-size: .9em; }
  th { background: #161b22; }
  input, button { font-family: inherit; padding: .4em .6em; border-radius: 4px; border: 1px solid #30363d; background:#161b22; color:#c9d1d9; }
  button { cursor:pointer; background:#238636; border-color:#2ea043; color:#fff; }
  button:hover { background:#2ea043; }
  button.danger { background:#da3633; border-color:#f85149; }
  .stat { display:inline-block; padding:.6em 1em; margin:.3em .5em .3em 0; background:#161b22; border:1px solid #30363d; border-radius:6px; }
  .stat b { display:block; font-size:1.6em; color:#58a6ff; }
  .stat span { font-size:.8em; color:#8b949e; }
  .muted { color:#8b949e; }
  #newKey { color:#3fb950; }
</style>
</head>
<body>
<h1>ManaTee Admin</h1>

<div id="login">
  <h2>Login</h2>
  <form id="loginForm">
    <input type="password" id="tokenInput" placeholder="admin token" autocomplete="off" />
    <button type="submit">Sign in</button>
    <span id="loginErr" class="muted"></span>
  </form>
</div>

<div id="panel" style="display:none">
  <h2>Stats</h2>
  <div id="statsBlock"></div>

  <h2>Create API key</h2>
  <input type="text" id="labelInput" placeholder="label (optional)" />
  <button id="createBtn">Create</button>
  <div id="newKey"></div>

  <h2>Keys</h2>
  <table id="keysTable">
    <thead><tr><th>Key</th><th>Label</th><th>Created</th><th>Requests</th><th>Status</th><th></th></tr></thead>
    <tbody></tbody>
  </table>

  <h2>Languages</h2>
  <table id="langsTable">
    <thead><tr><th>Language</th><th>Injections</th></tr></thead>
    <tbody></tbody>
  </table>

  <p><button id="logoutBtn" class="danger">Log out</button></p>
</div>

<script>
let TOKEN = localStorage.getItem("manatee_token") || "";

function api(path, opts = {}) {
  const headers = Object.assign({ "X-Admin-Token": TOKEN }, opts.headers || {});
  return fetch(path, Object.assign({}, opts, { headers })).then(async r => {
    if (!r.ok) throw new Error(await r.text());
    return r.json();
  });
}

function fmtTime(ts) {
  if (!ts) return "";
  return new Date(ts * 1000).toLocaleString();
}

async function refresh() {
  try {
    const [keys, stats] = await Promise.all([api("/admin/keys"), api("/admin/stats")]);
    document.getElementById("login").style.display = "none";
    document.getElementById("panel").style.display = "block";
    renderStats(stats);
    renderKeys(keys.keys);
    renderLangs(stats.languages || {});
  } catch (e) {
    document.getElementById("login").style.display = "block";
    document.getElementById("panel").style.display = "none";
  }
}

function renderStats(s) {
  const el = document.getElementById("statsBlock");
  el.innerHTML = `
    <div class="stat"><b>${s.total_keys||0}</b><span>total keys</span></div>
    <div class="stat"><b>${s.active_keys||0}</b><span>active keys</span></div>
    <div class="stat"><b>${s.requests||0}</b><span>requests</span></div>
    <div class="stat"><b>${s.injections_model||0}</b><span>injected by model</span></div>
    <div class="stat"><b>${s.injections_postprocess||0}</b><span>injected by proxy</span></div>
    <div class="stat"><b>${s.uptime||'0s'}</b><span>uptime</span></div>
  `;
}

function renderKeys(keys) {
  const tb = document.querySelector("#keysTable tbody");
  tb.innerHTML = "";
  for (const k of keys) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><code>${k.key}</code></td>
      <td>${k.label || ""}</td>
      <td>${fmtTime(k.created)}</td>
      <td>${k.requests || 0}</td>
      <td>${k.active ? "✅ active" : "⛔ revoked"}</td>
      <td></td>
    `;
    if (k.active) {
      const btn = document.createElement("button");
      btn.className = "danger";
      btn.textContent = "Revoke";
      btn.onclick = async () => {
        if (!confirm("Revoke " + k.key + " ?")) return;
        await api("/admin/revoke?key=" + encodeURIComponent(k.key), { method: "POST" });
        refresh();
      };
      tr.lastElementChild.appendChild(btn);
    }
    tb.appendChild(tr);
  }
}

function renderLangs(langs) {
  const tb = document.querySelector("#langsTable tbody");
  tb.innerHTML = "";
  const entries = Object.entries(langs).sort((a, b) => b[1] - a[1]);
  if (!entries.length) {
    tb.innerHTML = `<tr><td colspan="2" class="muted">no injections yet</td></tr>`;
    return;
  }
  for (const [lang, n] of entries) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${lang}</td><td>${n}</td>`;
    tb.appendChild(tr);
  }
}

document.getElementById("loginForm").onsubmit = async (e) => {
  e.preventDefault();
  const token = document.getElementById("tokenInput").value;
  try {
    await fetch("/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token })
    }).then(async r => { if (!r.ok) throw new Error(await r.text()); });
    TOKEN = token;
    localStorage.setItem("manatee_token", token);
    document.getElementById("loginErr").textContent = "";
    refresh();
  } catch (e) {
    document.getElementById("loginErr").textContent = "bad token";
  }
};

document.getElementById("createBtn").onclick = async () => {
  const label = document.getElementById("labelInput").value;
  const r = await api("/admin/keys?label=" + encodeURIComponent(label), { method: "POST" });
  document.getElementById("newKey").textContent = "New key: " + r.key;
  refresh();
};

document.getElementById("logoutBtn").onclick = () => {
  TOKEN = "";
  localStorage.removeItem("manatee_token");
  refresh();
};

refresh();
</script>
</body>
</html>
"""
