# blazar-ai

Local dual-agent system powered by Qwen3-30B-A3B (MoE), optimized for CPU-only mini PCs like the KOOSMILE (i9-12900HK + 32 GB DDR4, Iris Xe).

- **Coding Agent**: Build apps, games, projects
- **Trading Agent**: Educational paper-trading across blockchains (safe, no real funds)
- **Gradio UI**: Project workspace with chat, file open/save/editor, and basic media generation (icons & backgrounds via SVG + procedural)
- **Dark cosmic theme** matching Blazar Force

## Super Simple Start (Download → Install → Double-Click)

### 1. Prerequisites
- Python 3.10+
- Ollama installed and running (`ollama serve`). Download from https://ollama.com if needed.

### 2. Install
```bash
git clone https://github.com/cannergtfo-commits/blazar-ai.git
cd blazar-ai
python setup.py
```

This automatically:
- Installs Python dependencies
- **Pulls the model** (`ollama pull qwen3:30b-a3b`) and creates the CPU-tuned version
- Creates workspace + sample project
- Initializes memory
- **Creates a desktop shortcut** (`blazar-ai.bat` on Windows)

### 3. Run
**Double-click the `blazar-ai.bat` shortcut on your Desktop**

(or double-click `start_ui.bat` in this folder)

It will start the UI and automatically open http://localhost:7860 in your browser.

## Hardware Notes (KOOSMILE)
- Q4_K_M quantization, 16k context, ~12 threads recommended
- Media generation is CPU-friendly (SVG + Pillow procedural)
- Keep ~8-10 GB free RAM while the model is loaded

Educational use only for the trading agent. Never risk real funds.
