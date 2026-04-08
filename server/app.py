"""
server/app.py — FastAPI Application for Cloud SRE Sandbox

Creates the OpenEnv MCP server with a built-in web dashboard UI at the root /.
The dashboard shows live environment state and lets you interact with SRE tools.
"""

import os

try:
    from openenv.core.env_server.http_server import create_app
    from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation
    from .sre_environment import SREEnvironment
except ImportError:
    from openenv.core.env_server.http_server import create_app
    from openenv.core.env_server.mcp_types import CallToolAction, CallToolObservation
    from server.sre_environment import SREEnvironment

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Create the OpenEnv MCP app
app = create_app(
    SREEnvironment,
    CallToolAction,
    CallToolObservation,
    env_name="cloud_sre_env",
)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>☁️ Cloud SRE Sandbox — OpenEnv</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
  :root {
    --bg: #0a0e1a; --surface: #111827; --card: #1a2235; --border: #1e3a5f;
    --blue: #3b82f6; --cyan: #06b6d4; --green: #10b981; --red: #ef4444;
    --yellow: #f59e0b; --purple: #8b5cf6; --text: #e2e8f0; --muted: #64748b;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
  header { background: linear-gradient(135deg, #0f172a, #1e1b4b); border-bottom: 1px solid var(--border); padding: 20px 40px; display: flex; align-items: center; justify-content: space-between; }
  header h1 { font-size: 1.4rem; font-weight: 700; background: linear-gradient(90deg, var(--cyan), var(--blue)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .badge { background: #10b98122; color: var(--green); border: 1px solid var(--green); border-radius: 20px; padding: 4px 14px; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.05em; }
  .main { max-width: 1200px; margin: 0 auto; padding: 32px 20px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 24px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; }
  .card h2 { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
  .card h2 span { font-size: 1rem; }
  .incident { background: #7f1d1d22; border: 1px solid #ef444444; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; font-size: 0.85rem; display: flex; gap: 10px; align-items: flex-start; }
  .incident .icon { font-size: 1rem; flex-shrink: 0; margin-top: 1px; }
  .metric-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #ffffff08; font-size: 0.85rem; }
  .metric-row:last-child { border-bottom: none; }
  .metric-val { font-family: 'JetBrains Mono', monospace; font-weight: 600; }
  .metric-val.bad { color: var(--red); }
  .metric-val.warn { color: var(--yellow); }
  .metric-val.good { color: var(--green); }
  .tool-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
  .tool-btn { background: linear-gradient(135deg, #1e40af22, #1e3a5f44); border: 1px solid var(--border); border-radius: 10px; padding: 16px; cursor: pointer; text-align: left; transition: all 0.2s; color: var(--text); font-family: 'Inter', sans-serif; }
  .tool-btn:hover { background: linear-gradient(135deg, #1e40af44, #1e3a5f66); border-color: var(--blue); transform: translateY(-2px); }
  .tool-btn .tool-name { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: var(--cyan); font-weight: 500; }
  .tool-btn .tool-desc { font-size: 0.78rem; color: var(--muted); margin-top: 6px; line-height: 1.4; }
  .output-box { background: #050810; border: 1px solid var(--border); border-radius: 10px; padding: 20px; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; min-height: 140px; max-height: 300px; overflow-y: auto; white-space: pre-wrap; color: #a3e635; line-height: 1.6; }
  .output-box .placeholder { color: var(--muted); font-style: italic; }
  .actions-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
  .btn-primary { background: linear-gradient(135deg, var(--blue), var(--purple)); border: none; border-radius: 8px; padding: 10px 22px; color: white; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: opacity 0.2s; font-family: 'Inter', sans-serif; }
  .btn-primary:hover { opacity: 0.85; }
  .btn-danger { background: linear-gradient(135deg, var(--red), #b91c1c); border: none; border-radius: 8px; padding: 10px 22px; color: white; font-size: 0.85rem; font-weight: 600; cursor: pointer; font-family: 'Inter', sans-serif; }
  .btn-danger:hover { opacity: 0.85; }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
  .status-dot.running { background: var(--green); box-shadow: 0 0 8px var(--green); animation: pulse 2s infinite; }
  .status-dot.crashed { background: var(--red); box-shadow: 0 0 8px var(--red); }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
  .tag { display: inline-block; background: #1e40af33; color: var(--blue); border: 1px solid #3b82f644; border-radius: 4px; padding: 2px 8px; font-size: 0.72rem; font-family: 'JetBrains Mono', monospace; margin: 2px; }
  .section-title { font-size: 1rem; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 10px; }
  footer { text-align: center; padding: 32px; color: var(--muted); font-size: 0.8rem; border-top: 1px solid var(--border); margin-top: 40px; }
  footer a { color: var(--blue); text-decoration: none; }
</style>
</head>
<body>
<header>
  <div>
    <div style="font-size:0.75rem;color:var(--muted);margin-bottom:4px">META PYTORCH HACKATHON · OPENENV</div>
    <h1>☁️ Cloud SRE Sandbox</h1>
  </div>
  <div style="display:flex;gap:12px;align-items:center">
    <span class="badge">● RUNNING</span>
    <span style="font-size:0.78rem;color:var(--muted)">v0.1.0 · Docker · cpu-basic</span>
  </div>
</header>

<div class="main">

  <!-- Active Incidents -->
  <div class="card" style="margin-bottom:24px;border-color:#ef444433">
    <h2><span>🚨</span> Active Incidents (3)</h2>
    <div class="incident"><span class="icon">💥</span><div><b>web-app</b> — Out of Memory crash. CPU: 98.5%, RAM: 99.2%. Process killed by OOM killer.</div></div>
    <div class="incident"><span class="icon">🔌</span><div><b>database</b> — Connection pool exhausted (1000/1000). Query latency: 4500 ms.</div></div>
    <div class="incident"><span class="icon">⚠️</span><div><b>web-app v2.1</b> — Bad deployment causing 87% HTTP 500 errors on /api/checkout.</div></div>
  </div>

  <div class="grid">
    <!-- web-app metrics -->
    <div class="card">
      <h2><span>🌐</span> web-app</h2>
      <div class="metric-row"><span>Status</span><span class="metric-val bad"><span class="status-dot crashed"></span>CRASHED</span></div>
      <div class="metric-row"><span>CPU Usage</span><span class="metric-val bad">98.5%</span></div>
      <div class="metric-row"><span>RAM Usage</span><span class="metric-val bad">99.2%</span></div>
      <div class="metric-row"><span>Version</span><span class="metric-val warn">v2.1 (bad)</span></div>
      <div class="metric-row"><span>Error Rate</span><span class="metric-val bad">87%</span></div>
    </div>

    <!-- database metrics -->
    <div class="card">
      <h2><span>🗄️</span> database</h2>
      <div class="metric-row"><span>Status</span><span class="metric-val warn"><span class="status-dot" style="background:var(--yellow)"></span>DEGRADED</span></div>
      <div class="metric-row"><span>Connections</span><span class="metric-val bad">1000 / 1000</span></div>
      <div class="metric-row"><span>Query Latency</span><span class="metric-val bad">4500 ms</span></div>
      <div class="metric-row"><span>Pool Status</span><span class="metric-val bad">EXHAUSTED</span></div>
    </div>
  </div>

  <!-- MCP Tools -->
  <div class="card" style="margin-bottom:24px">
    <h2><span>🛠️</span> MCP Tools — SRE Actions</h2>
    <div class="tool-grid">
      <button class="tool-btn" onclick="callTool('read_metrics',{service:'all'})">
        <div class="tool-name">read_metrics</div>
        <div class="tool-desc">Get CPU, RAM, connections, latency for all services</div>
      </button>
      <button class="tool-btn" onclick="callTool('read_logs',{service:'all'})">
        <div class="tool-name">read_logs</div>
        <div class="tool-desc">Read error and warning logs for all services</div>
      </button>
      <button class="tool-btn" onclick="callTool('restart_service',{service:'web-app'})">
        <div class="tool-name">restart_service</div>
        <div class="tool-desc">Restart web-app to recover from OOM crash</div>
      </button>
      <button class="tool-btn" onclick="callTool('scale_up',{service:'database',max_connections:2000})">
        <div class="tool-name">scale_up</div>
        <div class="tool-desc">Scale database connections from 1000 → 2000</div>
      </button>
      <button class="tool-btn" onclick="callTool('rollback_deployment',{service:'web-app',version:'v2.0'})">
        <div class="tool-name">rollback_deployment</div>
        <div class="tool-desc">Rollback web-app from v2.1 → v2.0</div>
      </button>
    </div>
  </div>

  <!-- API Console -->
  <div class="card">
    <div class="section-title">⚡ Live API Console</div>
    <div class="actions-row">
      <button class="btn-primary" onclick="resetEnv()">🔄 Reset Environment</button>
      <button class="btn-primary" onclick="window.open('/docs','_blank')">📖 Swagger API Docs</button>
      <button class="btn-danger" onclick="clearOutput()">🗑 Clear</button>
    </div>
    <div class="output-box" id="output"><span class="placeholder">// Click a tool button above or Reset to start...
// All API calls go to: POST /step</span></div>
  </div>

  <!-- Tags -->
  <div style="margin-top:20px;text-align:center">
    <span class="tag">OpenEnv</span>
    <span class="tag">MCP</span>
    <span class="tag">FastMCP</span>
    <span class="tag">FastAPI</span>
    <span class="tag">Docker</span>
    <span class="tag">SRE</span>
    <span class="tag">Meta PyTorch Hackathon</span>
  </div>
</div>

<footer>
  <p>Cloud SRE Sandbox · Built for <a href="https://github.com/meta-pytorch/OpenEnv" target="_blank">Meta OpenEnv Hackathon</a> ·
  API: <a href="/docs" target="_blank">/docs</a> ·
  GitHub: <a href="https://github.com/challau/cloud-sre-env" target="_blank">challau/cloud-sre-env</a></p>
</footer>

<script>
const out = document.getElementById('output');

function log(msg) {
  const ts = new Date().toLocaleTimeString();
  out.textContent = '[' + ts + '] ' + msg + '\\n\\n' + out.textContent;
}

async function resetEnv() {
  log('POST /reset ...');
  try {
    const r = await fetch('/reset', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
    const d = await r.json();
    log('RESET OK → ' + JSON.stringify(d, null, 2));
  } catch(e) { log('ERROR: ' + e); }
}

async function callTool(name, args) {
  log('Calling tool: ' + name + '(' + JSON.stringify(args) + ')');
  try {
    const r = await fetch('/step', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({action_type:'CallToolAction', tool_name: name, arguments: args})
    });
    const d = await r.json();
    log(name + ' → ' + JSON.stringify(d, null, 2));
  } catch(e) { log('ERROR: ' + e); }
}

function clearOutput() {
  out.innerHTML = '<span class="placeholder">// Console cleared.</span>';
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard():
    """Serve the Cloud SRE Sandbox web dashboard."""
    return HTMLResponse(content=DASHBOARD_HTML)


def main():
    import uvicorn
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
