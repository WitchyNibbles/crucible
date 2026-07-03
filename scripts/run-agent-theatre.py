"""Launch and inspect the agent-theatre Crucible delivery."""
from pathlib import Path
from crucible.runner import WorkflowRunner, FakeAgentBridge

fixtures = {
    "python": {
        "app.py": '''"""Agent Theatre Flask app."""
from __future__ import annotations

from flask import Flask, jsonify, render_template

app = Flask(__name__)

AGENTS = [
    {"id": "researcher", "name": "Ivy", "emoji": "🧠", "location": "library", "status": "researching"},
    {"id": "engineer",  "name": "Bolt", "emoji": "💻", "location": "computer", "status": "working"},
    {"id": "explainer", "name": "Vera", "emoji": "🎭", "location": "theatre", "status": "explaining"},
]


@app.get("/")
def index():
    return render_template("index.html", agents=AGENTS)


@app.get("/api/agents")
def agents():
    return jsonify(AGENTS)


if __name__ == "__main__":
    app.run(debug=True)
''',
        "routes.py": '''"""Routes for agent status."""
from __future__ import annotations

from agent_theatre.app import app


@app.get("/api/agents/<agent_id>/move")
def move(agent_id: str):
    return {"ok": True}
''',
        "load_agents.py": '''"""Load agent state."""
from __future__ import annotations


def load_agents():
    return [
        {"id": "researcher", "name": "Ivy", "emoji": "🧠"},
        {"id": "engineer",  "name": "Bolt", "emoji": "💻"},
        {"id": "explainer", "name": "Vera", "emoji": "🎭"},
    ]
''',
        "README.md": "# Agent Theatre\n\nCute character dashboard.\n",
        "templates/index.html": "<html><body><h1>Agent Theatre</h1><p>Characters: Ivy, Bolt, Vera</p></body></html>\n",
        "static/css/styles.css": "body { background:#0f172a; color:#e2e8f0; font-family:system-ui; }\n.panel { background:#1e293b; border-radius:.75rem; padding:1rem; }\n",
    },
    "typescript": {
        "styles.css": "/* Agent Theatre theme */\nbody { background:#0f172a; color:#e2e8f0; font-family:system-ui; }\n.panel { background:#1e293b; border-radius:.75rem; padding:1rem; }\n",
        "app.ts": "console.log('Agent Theatre ready');\n",
        "README.md": "# Agent Theatre frontend\n",
    },
}

repo_root = Path("/home/eimi/projects/agent-theatre")
state_dir = Path("/home/eimi/.crucible/state")
log_dir = Path("/home/eimi/.crucible/log")

for stale in [
    repo_root / "src/agent_theatre/templates",
    repo_root / "src/agent_theatre/static",
]:
    if stale.exists() and stale.is_dir() and not any(stale.iterdir()):
        stale.rmdir()

runner = WorkflowRunner(
    "agent-theatre",
    requirements="Build a cute Python Flask web app showing 3 agent characters: researcher/library, engineer/computer, explainer/theatre.",
    repo_root=repo_root,
    state_dir=state_dir,
    log_dir=log_dir,
    agent_bridge=FakeAgentBridge(fixtures),
)
runner.add_disciplines({
    "engineering": ["backend", "frontend", "qa"],
})

report = runner.run()
print(report)

app_py = repo_root / "src" / "engineering" / "backend" / "python" / "app.py"
print("app.py exists:", app_py.exists())
if app_py.exists():
    print(app_py.read_text())
