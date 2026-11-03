# blazar-ai

Local dual-agent system powered by Qwen3-30B-A3B (MoE), optimized for CPU-only mini PCs like the KOOSMILE (i9-12900HK + 32 GB DDR4, Iris Xe).

- **Coding Agent**: Build apps, games, projects
- **Trading Agent**: Educational paper-trading across blockchains (safe, no real funds)
- **Gradio UI**: Project workspace with chat, file open/save/editor, and basic media generation (icons & backgrounds via SVG + procedural)

## Quick Start (Download → Installer → Use)

### 1. Prerequisites
- Python 3.10+
- Ollama installed and running (`ollama serve`). Download from https://ollama.com if needed.

### 2. Install / Setup
```bash
git clone https://github.com/cannergtfo-commits/blazar-ai.git
cd blazar-ai
python setup.py
```

This automatically:
- Installs Python dependencies
- Pulls `qwen3:30b-a3b`
- Creates the CPU-tuned model `qwen3-30b-cpu`
- Creates workspace + sample project
- Initializes memory databases

### 3. Launch UI
```bash
python ui/app.py
```

Open http://localhost:7860

### Alternative start scripts
- Linux/macOS: `bash start_ui.sh`
- Windows: `start_ui.bat`

## Hardware Notes (KOOSMILE)
- Q4_K_M quantization, 16k context, ~12 threads recommended
- Media generation is CPU-friendly (SVG + Pillow procedural) — no heavy diffusion models by default
- Keep ~8-10 GB free RAM while the model is loaded

## Structure
- `agents/` — coding and trading agents with SQLite memory
- `ui/` — Gradio project workspace UI
- `setup.py` — one-command installer
- `Modelfile.cpu` — CPU-optimized model definition
- `workspace/` — your projects live here

Educational use only for the trading agent. Never risk real funds.
