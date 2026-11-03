import gradio as gr
from pathlib import Path

WORKSPACE = Path("workspace")
WORKSPACE.mkdir(exist_ok=True)

def list_files():
    files = []
    for p in WORKSPACE.rglob("*"):
        if p.is_file() and not p.name.startswith("."):
            files.append(str(p.relative_to(WORKSPACE)))
    return sorted(files) or ["(empty)"]

def open_file(filename):
    if not filename or filename == "(empty)":
        return ""
    path = WORKSPACE / filename
    if path.exists():
        return path.read_text(errors="ignore")
    return ""

def save_file(filename, content):
    if not filename:
        return "No filename"
    path = WORKSPACE / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return f"Saved {filename}"

def chat_fn(message, history, agent):
    return f"[{agent}] Received: {message}\n\n(Full agent integration coming — model qwen3-30b-cpu)"

def generate_svg(prompt):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0a0a12"/>
      <stop offset="100%" style="stop-color:#1a0a2e"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" fill="url(#bg)"/>
  <circle cx="32" cy="32" r="18" fill="none" stroke="#00d4ff" stroke-width="2"/>
  <circle cx="32" cy="32" r="8" fill="#e94560"/>
  <text x="32" y="48" text-anchor="middle" fill="#00d4ff" font-size="6">{prompt[:8]}</text>
</svg>'''
    return svg

# BlazarForce-inspired dark cosmic theme
custom_css = """
.gradio-container {
    background: linear-gradient(135deg, #0a0a12 0%, #0d1117 50%, #1a0a2e 100%) !important;
    color: #e0e0e0 !important;
    font-family: 'Inter', system-ui, sans-serif;
}
.gr-button {
    background: linear-gradient(90deg, #e94560, #00d4ff) !important;
    border: none !important;
    color: white !important;
    border-radius: 8px !important;
}
.gr-button:hover {
    opacity: 0.9;
    transform: translateY(-1px);
}
.gr-box, .gr-panel {
    background: rgba(13, 17, 23, 0.8) !important;
    border: 1px solid #00d4ff33 !important;
    border-radius: 12px !important;
}
.gr-input, .gr-textbox, .gr-dropdown {
    background: #0d1117 !important;
    border: 1px solid #00d4ff55 !important;
    color: #e0e0e0 !important;
}
h1, h2, .gr-markdown {
    color: #00d4ff !important;
}
"""

with gr.Blocks(title="blazar-ai — Project Workspace", css=custom_css, theme=gr.themes.Base()) as demo:
    gr.Markdown("# ✨ blazar-ai\n**Local Qwen agents** — cosmic project workspace for the KOOSMILE")
    with gr.Row():
        agent = gr.Radio(["Coding", "Trading (Edu)"], value="Coding", label="Agent")
    with gr.Row():
        with gr.Column(scale=1):
            file_dd = gr.Dropdown(choices=list_files(), label="Files in workspace")
            refresh = gr.Button("Refresh")
            open_btn = gr.Button("Open")
            save_btn = gr.Button("Save")
        with gr.Column(scale=3):
            with gr.Tabs():
                with gr.Tab("Chat"):
                    chatbot = gr.Chatbot(height=400)
                    msg = gr.Textbox(label="Message", placeholder="Ask the agent...")
                    msg.submit(chat_fn, [msg, chatbot, agent], chatbot)
                with gr.Tab("Editor"):
                    editor = gr.Code(language="python", lines=20, label="File content")
                with gr.Tab("Media Gen"):
                    media_prompt = gr.Textbox(label="Icon / Background prompt")
                    gen_btn = gr.Button("Generate SVG Icon")
                    media_out = gr.HTML()
                    gen_btn.click(lambda p: f"<div style='background:#0a0a12;padding:20px;border-radius:12px'>{generate_svg(p)}</div>", media_prompt, media_out)

    open_btn.click(open_file, file_dd, editor)
    save_btn.click(save_file, [file_dd, editor], gr.Textbox(visible=False))
    refresh.click(lambda: gr.Dropdown(choices=list_files()), outputs=file_dd)

if __name__ == "__main__":
    demo.launch()
