"""Blazar AI setup: deps, Ollama, model, workspace, desktop shortcut."""
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import urllib.request

ROOT = Path(__file__).resolve().parent
OLLAMA = "http://localhost:11434"
BIG, SMALL = "qwen3:30b-a3b", "qwen3:8b"


def step(t):
    print("\n=== " + t + " ===")


def ram_gb():
    try:
        if os.name == "nt":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("m", ctypes.c_ulong), ("t", ctypes.c_ulonglong),
                            ("a", ctypes.c_ulonglong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                            ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ae", ctypes.c_ulonglong)]
            s = MS(); s.l = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
            return s.t / 2**30
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
    except Exception:
        return 0


def find_ollama():
    exe = shutil.which("ollama")
    if exe:
        return exe
    for c in [Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Ollama/ollama.exe",
              Path("/usr/local/bin/ollama"), Path("/usr/bin/ollama")]:
        if c.is_file():
            return str(c)
    return None


def ollama_up():
    try:
        urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3)
        return True
    except Exception:
        return False


def desktop_dir():
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf)  # CSIDL_DESKTOPDIRECTORY
            if buf.value:
                return Path(buf.value)
        except Exception:
            pass
    d = Path.home() / "Desktop"
    return d if d.exists() else None


def main():
    step("Installing Python packages")
    r = subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", "-r", str(ROOT / "requirements.txt")])
    if r != 0:
        r = subprocess.call([sys.executable, "-m", "pip", "install", "--user", "-r", str(ROOT / "requirements.txt")])
    if r != 0:
        print("WARNING: pip install failed. Try: python -m pip install -r requirements.txt")

    step("Checking Ollama")
    exe = find_ollama()
    if not exe:
        print("Ollama not found. Install it from https://ollama.com then re-run setup.")
    elif not ollama_up():
        print("Starting 'ollama serve' in the background...")
        flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
        subprocess.Popen([exe, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        for _ in range(30):
            if ollama_up():
                break
            time.sleep(1)
    print("Ollama running." if ollama_up() else "WARNING: Ollama is not responding yet.")

    model = os.environ.get("BLAZAR_MODEL")
    if not model:
        gb = ram_gb()
        model = BIG
        if gb and gb < 24:
            print(f"Detected {gb:.0f} GB RAM - {BIG} needs ~24 GB. Using smaller {SMALL}.")
            model = SMALL
    (ROOT / ".blazar_model").write_text(model, encoding="utf-8")
    if exe:
        step(f"Downloading model {model} (can take a while)")
        if subprocess.call([exe, "pull", model]) != 0:
            print(f"WARNING: model pull failed. Later run: ollama pull {model}")

    step("Creating workspace")
    ws = ROOT / "workspace" / "sample_project"
    ws.mkdir(parents=True, exist_ok=True)
    (ROOT / "workspace" / "memory").mkdir(exist_ok=True)
    if not (ws / "hello.py").exists():
        (ws / "hello.py").write_text('print("Hello from Blazar AI!")\n', encoding="utf-8")
        (ws / "README.md").write_text("# Sample project\nOpen files here from the Workspace tab.\n", encoding="utf-8")

    step("Creating launcher")
    if os.name == "nt":
        desk = desktop_dir()
        if desk:
            bat = desk / "Blazar AI.bat"
            bat.write_text(f'@echo off\r\ncall "{ROOT / "start_ui.bat"}"\r\n', encoding="ascii", errors="replace")
            print(f"Desktop launcher: {bat}")
    else:
        sh = ROOT / "start_ui.sh"
        sh.write_text(f'#!/bin/sh\ncd "{ROOT}"\n(ollama serve >/dev/null 2>&1 &)\n"{sys.executable}" ui/app.py\n')
        sh.chmod(0o755)
        print(f"Launcher: {sh}")
    print(f"\nSetup complete on {platform.system()}. Model: {model}")


if __name__ == "__main__":
    main()
