"""Blazar AI - local Gradio workspace talking to Ollama."""
import inspect
import json
import os
import re
from pathlib import Path

import gradio as gr
import requests

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / "workspace"
PROMPTS = ROOT / "prompts"
MODEL_FILE = ROOT / ".blazar_model"
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
if not OLLAMA_URL.startswith("http"):
    OLLAMA_URL = "http://" + OLLAMA_URL


def default_model():
    if os.environ.get("BLAZAR_MODEL"):
        return os.environ["BLAZAR_MODEL"]
    if MODEL_FILE.exists():
        m = MODEL_FILE.read_text(encoding="utf-8").strip()
        if m:
            return m
    return "qwen3:30b-a3b"


MODEL = default_model()
AGENTS = {"Coding": "coding.txt", "Trading (Edu)": "trading.txt", "Idea -> Prompt": "idea_to_prompt.txt"}
DEFAULT_PROMPTS = {
    "coding.txt": "You are Blazar Coding Agent, an expert software engineer.",
    "trading.txt": "You are Blazar Trading Agent (Educational). Paper trading only, never real funds.",
    "idea_to_prompt.txt": "Turn the user's idea into a clear, structured agent prompt.",
}

WORKSPACE.mkdir(exist_ok=True)
PROMPTS.mkdir(exist_ok=True)


def load_prompt(agent):
    f = PROMPTS / AGENTS.get(agent, "coding.txt")
    if not f.exists():
        f.write_text(DEFAULT_PROMPTS[f.name], encoding="utf-8")
    return f.read_text(encoding="utf-8")


def save_prompt(agent, text):
    (PROMPTS / AGENTS[agent]).write_text(text, encoding="utf-8")
    return f"Saved system prompt for {agent}."


# ---------------- Ollama ----------------
FIX_HINT = (
    "**Ollama problem:** {err}\n\n"
    "How to fix:\n"
    "1. Make sure Ollama is installed (https://ollama.com) and running: open a terminal and run `ollama serve`.\n"
    "2. Make sure the model is downloaded: `ollama pull {model}`.\n"
    "3. Or re-run `setup_windows.bat`, which does both for you."
)


def clean_output(text):
    """Collapse <think> blocks into a <details> section."""
    def repl(m):
        inner = m.group(1).strip()
        return f"<details><summary>Thinking</summary>\n\n{inner}\n\n</details>\n\n" if inner else ""
    text = re.sub(r"<think>(.*?)</think>", repl, text, flags=re.S)
    if "<think>" in text:  # still streaming the thought
        before, _, inner = text.partition("<think>")
        text = before + "<details><summary>Thinking...</summary>\n\n" + inner + "\n\n</details>"
    return text.strip()


def ollama_stream(messages, model=None):
    model = model or MODEL
    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat",
                          json={"model": model, "messages": messages, "stream": True},
                          stream=True, timeout=(5, 600))
    except requests.exceptions.RequestException:
        yield FIX_HINT.format(err=f"could not reach Ollama at {OLLAMA_URL}.", model=model)
        return
    if r.status_code != 200:
        try:
            err = r.json().get("error", r.text)
        except Exception:
            err = r.text
        yield FIX_HINT.format(err=f"{err} (HTTP {r.status_code})", model=model)
        return
    out = ""
    for line in r.iter_lines():
        if not line:
            continue
        try:
            data = json.loads(line)
        except ValueError:
            continue
        if data.get("error"):
            yield FIX_HINT.format(err=data["error"], model=model)
            return
        out += data.get("message", {}).get("content", "")
        yield clean_output(out)
        if data.get("done"):
            break


def chat_send(message, history, agent):
    history = list(history or [])
    if not message or not message.strip():
        yield "", history
        return
    msgs = [{"role": "system", "content": load_prompt(agent)}]
    for h in history:
        msgs.append({"role": h["role"], "content": re.sub(r"<details>.*?</details>", "", str(h["content"]), flags=re.S)})
    msgs.append({"role": "user", "content": message})
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": "..."})
    yield "", history
    for partial in ollama_stream(msgs):
        history[-1]["content"] = partial or "..."
        yield "", history


# ---------------- Workspace ----------------
def list_files():
    return sorted(str(p.relative_to(WORKSPACE)).replace("\\", "/")
                  for p in WORKSPACE.rglob("*") if p.is_file())


def safe_path(name):
    p = (WORKSPACE / name).resolve()
    if WORKSPACE.resolve() not in p.parents and p != WORKSPACE.resolve():
        raise ValueError("Path must stay inside the workspace folder.")
    return p


def refresh():
    return gr.update(choices=list_files())


def open_file(name):
    if not name:
        return "", "", "Pick a file."
    try:
        return name, safe_path(name).read_text(encoding="utf-8", errors="replace"), f"Opened {name}"
    except Exception as e:
        return name, "", f"Error: {e}"


def save_file(name, content):
    if not name:
        return "Enter a file name.", gr.update()
    try:
        p = safe_path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content or "", encoding="utf-8")
        return f"Saved {name}", gr.update(choices=list_files(), value=name)
    except Exception as e:
        return f"Error: {e}", gr.update()


# ---------------- Media (SVG) ----------------
def make_svg(kind, text, c1, c2):
    text = (text or "B")[:24].replace("&", "&amp;").replace("<", "&lt;")
    if kind == "Icon":
        w = h = 256
        body = (f'<circle cx="128" cy="128" r="116" fill="url(#g)"/>'
                f'<text x="128" y="150" font-size="72" text-anchor="middle" fill="#fff" font-family="sans-serif">{text[:3]}</text>')
    else:
        w, h = 1280, 720
        stars = "".join(f'<circle cx="{(i*137)%w}" cy="{(i*251)%h}" r="{1+i%3}" fill="#fff" opacity="0.7"/>' for i in range(80))
        body = (f'<rect width="{w}" height="{h}" fill="url(#g)"/>{stars}'
                f'<text x="{w//2}" y="{h//2}" font-size="64" text-anchor="middle" fill="#fff" font-family="sans-serif">{text}</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
           f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/>'
           f'<stop offset="1" stop-color="{c2}"/></linearGradient></defs>{body}</svg>')
    out = WORKSPACE / "media"
    out.mkdir(exist_ok=True)
    fname = f"{kind.lower()}_{re.sub(r'[^A-Za-z0-9]+', '_', text) or 'x'}.svg"
    (out / fname).write_text(svg, encoding="utf-8")
    return svg, f"Saved workspace/media/{fname}"


CSS = """
body, .gradio-container {background: radial-gradient(ellipse at top, #1b1040 0%, #07071a 70%) !important; color:#e6e6ff;}
h1 {background: linear-gradient(90deg,#8a5cff,#34d1ff); -webkit-background-clip:text; color:transparent !important;}
button.primary {background: linear-gradient(90deg,#6a3cff,#1fa8ff) !important; border:none !important;}
"""


def build():
    with gr.Blocks(title="Blazar AI") as demo:
        gr.Markdown(f"# Blazar AI\nLocal agents via Ollama - model: `{MODEL}`")
        with gr.Tab("Chat"):
            agent = gr.Radio(list(AGENTS), value="Coding", label="Agent")
            kw = {"type": "messages"} if "type" in inspect.signature(gr.Chatbot.__init__).parameters else {}
            bot = gr.Chatbot(height=480, **kw)
            with gr.Row():
                msg = gr.Textbox(placeholder="Type and press Enter to send", show_label=False, scale=8)
                send = gr.Button("Send", variant="primary", scale=1)
            clear = gr.Button("Clear chat")
            msg.submit(chat_send, [msg, bot, agent], [msg, bot])
            send.click(chat_send, [msg, bot, agent], [msg, bot])
            clear.click(lambda: [], None, bot)
        with gr.Tab("Edit Prompt"):
            pa = gr.Dropdown(list(AGENTS), value="Coding", label="Agent")
            ptext = gr.Textbox(value=load_prompt("Coding"), lines=14, label="System prompt")
            psave = gr.Button("Save prompt", variant="primary")
            pstat = gr.Markdown()
            pa.change(load_prompt, pa, ptext)
            psave.click(save_prompt, [pa, ptext], pstat)
        with gr.Tab("Workspace / Editor"):
            with gr.Row():
                files = gr.Dropdown(list_files(), label="Workspace files", scale=4)
                rbtn = gr.Button("Refresh", scale=1)
            fname = gr.Textbox(label="File name (relative to workspace/)")
            editor = gr.Code(label="Editor", lines=22)
            with gr.Row():
                obtn = gr.Button("Open")
                sbtn = gr.Button("Save", variant="primary")
            fstat = gr.Markdown()
            rbtn.click(refresh, None, files)
            files.change(open_file, files, [fname, editor, fstat])
            obtn.click(open_file, files, [fname, editor, fstat])
            sbtn.click(save_file, [fname, editor], [fstat, files])
        with gr.Tab("Media Gen"):
            kind = gr.Radio(["Icon", "Background"], value="Icon", label="Type")
            mtext = gr.Textbox(value="BZ", label="Text")
            with gr.Row():
                c1 = gr.ColorPicker(value="#6a3cff", label="Color 1")
                c2 = gr.ColorPicker(value="#1fa8ff", label="Color 2")
            gbtn = gr.Button("Generate", variant="primary")
            preview = gr.HTML()
            mstat = gr.Markdown()
            gbtn.click(make_svg, [kind, mtext, c1, c2], [preview, mstat])
    return demo


if __name__ == "__main__":
    demo = build()
    kwargs = {"server_name": os.environ.get("BLAZAR_HOST", "127.0.0.1"),
              "server_port": int(os.environ.get("BLAZAR_PORT", "7860"))}
    params = inspect.signature(demo.launch).parameters
    if "css" in params:
        kwargs["css"] = CSS
        kwargs["theme"] = gr.themes.Soft(primary_hue="violet")
    else:  # older Gradio: css lives on Blocks
        demo.css = CSS
    demo.queue().launch(**kwargs)
