# blazar-ai

Local dual-agent workspace powered by Qwen3 via Ollama, with a Gradio UI and a dark cosmic theme.

- **Coding Agent** - build apps, games, projects
- **Trading Agent (Edu)** - educational paper trading only, never real funds
- **Idea -> Prompt** - turns plain ideas into structured agent prompts
- **Edit Prompt tab** - view and edit each agent's system prompt (saved in `prompts/`)
- **Workspace / Editor** - open, edit and save files in `workspace/`
- **Media Gen** - SVG icons and backgrounds

## Install (Windows, 3 steps)

1. On GitHub click **Code -> Download ZIP**, then extract it anywhere.
2. Double-click **`setup_windows.bat`**. It installs Python and Ollama if missing, installs packages,
   downloads the model and creates a **Blazar AI** launcher on your Desktop.
3. Double-click **Blazar AI** on your Desktop. The browser opens at http://localhost:7860.

Model: `qwen3:30b-a3b` (needs about 24 GB RAM). On PCs with less RAM, setup picks `qwen3:8b` automatically.
Override with the `BLAZAR_MODEL` environment variable before running setup.

## Mac / Linux

```
python3 setup.py
./start_ui.sh
```
(Install Ollama first from https://ollama.com.)

## Troubleshooting
- Chat says "Ollama problem": run `ollama serve`, then `ollama pull <model>`, or re-run setup.
- Port busy: set `BLAZAR_PORT` to another port.

Educational use only for the trading agent. Never risk real funds.
