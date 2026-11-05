"""Blazar AI unattended job runner (main-PC GPU edition).

One pass over queue/*.json then exit. Never pushes. Never runs arbitrary
commands. AI edits happen only in a git worktree on branch blazar-ai/<id>.
Preset jobs (build/navmesh/lighting/cook/test) run in the main project and
do not commit.

GPU rules for the main PC:
- Refuse to start if UnrealEditor, UnrealEditor-Cmd (interactive), or a
  packaged Blazarshootem game process is running.
- Unload the Ollama model (keep_alive=0 / ollama stop) when finished.
- Runs ONLY when the user launches start.bat / runner.py (no overnight window,
  no scheduled task). Honors paused.flag. Optional --require-idle skips start
  when the PC is under heavy load.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime

HOME = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HOME, "config.json"), encoding="utf-8-sig"))
PROJECT = CFG["project"]
GIT = CFG["git"]
UE = CFG["engine"]
OLLAMA = CFG.get("ollama", "http://localhost:11434").rstrip("/")
MODEL = CFG.get("model", "qwen2.5-coder:14b")
NUM_CTX = int(CFG.get("num_ctx", 8192))
MODEL_TIMEOUT = int(CFG.get("model_timeout_s", 1800))
MAX_RETRIES = int(CFG.get("max_retries", 3))
IDLE_CPU_PCT = float(CFG.get("idle_cpu_pct", 35.0))

Q, RUN, DONE, WT, REPORTS = [
    os.path.join(HOME, d) for d in ("queue", "running", "done", "worktrees", "reports")
]
for d in (Q, RUN, DONE, WT, REPORTS):
    os.makedirs(d, exist_ok=True)

DENY = re.compile(
    r"(^|[\\/])(\.git|Binaries|Intermediate|Saved|DerivedDataCache|Engine)([\\/]|$)|"
    r"chain|wallet|web3|solana|polygon|blockchain|rpc|crypto|token|secret|\.env",
    re.I,
)
TEXT_EXT = {".cpp", ".h", ".hpp", ".cs", ".py", ".md", ".txt", ".ini", ".json", ".log", ".uplugin", ".build.cs"}
UPROJ = "Blazarshootem.uproject"
BUSY_PROCS = (
    "unrealeditor.exe",
    "unrealeditor-cmd.exe",
    "blazarshootem.exe",
    "blazarshootem-win64-shipping.exe",
    "blazarshootemeditor.exe",
)


def log(lf, msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S ") + str(msg)
    print(line)
    if lf is not None:
        lf.write(line + "\n")
        lf.flush()


def run(lf, args, cwd, timeout):
    log(lf, "RUN " + " ".join(args))
    env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1")
    p = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        errors="replace",
        env=env,
    )
    out = (p.stdout or "")[-6000:]
    err = "\n".join(
        l for l in (p.stderr or "").splitlines() if "Updating files" not in l
    )[-3000:]
    log(lf, f"exit={p.returncode}\n{out}\n{err}")
    return p.returncode, out, err


def safe_rel(wt, rel):
    if os.path.isabs(rel) or ".." in rel.replace("\\", "/").split("/") or DENY.search(rel):
        raise ValueError("path not allowed: " + rel)
    full = os.path.realpath(os.path.join(wt, rel))
    root = os.path.realpath(wt)
    if not (full == root or full.startswith(root + os.sep)):
        raise ValueError("escapes worktree: " + rel)
    if os.path.splitext(rel)[1].lower() not in TEXT_EXT:
        raise ValueError("not a text file type: " + rel)
    return full


def list_busy_procs():
    try:
        out = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=30,
            errors="replace",
        ).stdout.lower()
    except Exception:
        return []
    hit = []
    for name in BUSY_PROCS:
        if name in out:
            hit.append(name)
    return hit


def editor_or_game_running():
    return bool(list_busy_procs())


def cpu_busy_pct(sample_s=2.0):
    """Rough whole-machine CPU busy % via typeperf (Windows)."""
    try:
        p = subprocess.run(
            ["typeperf", r"\Processor(_Total)\% Processor Time", "-sc", "1"],
            capture_output=True,
            text=True,
            timeout=sample_s + 10,
            errors="replace",
        )
        # Last quoted float on a data line.
        for line in reversed(p.stdout.splitlines()):
            m = re.findall(r'"([0-9.]+)"', line)
            if m:
                return float(m[-1])
    except Exception:
        pass
    return 0.0


def pc_idle_enough():
    return cpu_busy_pct() < IDLE_CPU_PCT


def ollama_request(path, payload=None, method=None, timeout=60):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        OLLAMA + path,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method or ("POST" if data else "GET"),
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def unload_model(lf=None):
    """Free VRAM so Unreal can take the GPU later."""
    try:
        # keep_alive 0 on a tiny generate forces unload of the named model.
        ollama_request(
            "/api/generate",
            {
                "model": MODEL,
                "prompt": "",
                "keep_alive": 0,
                "stream": False,
            },
            timeout=120,
        )
        log(lf, f"unloaded model {MODEL} (keep_alive=0)")
    except Exception as e:
        log(lf, f"unload keep_alive failed: {e}")
    try:
        subprocess.run(
            [CFG.get("ollama_exe", "ollama"), "stop", MODEL],
            capture_output=True,
            text=True,
            timeout=60,
        )
        log(lf, f"ollama stop {MODEL}")
    except Exception as e:
        log(lf, f"ollama stop failed: {e}")


def preset(name, root, t):
    """Fixed command presets. Task may only pick a name (+ optional /Game map)."""
    up = os.path.join(root, UPROJ)
    ed = os.path.join(UE, r"Engine\Binaries\Win64\UnrealEditor-Cmd.exe")
    ubt = os.path.join(UE, r"Engine\Build\BatchFiles\Build.bat")
    common = ["-unattended", "-nopause", "-nosplash", "-stdout", "-FullStdOutLogOutput"]
    mp = t.get("map", "")
    if mp and not re.fullmatch(r"/Game/[A-Za-z0-9_/]+", mp):
        raise ValueError("bad map")
    maparg = ["-map=" + mp.rsplit("/", 1)[1]] if mp else []
    if name == "build":
        return [ubt, "BlazarshootemEditor", "Win64", "Development", f"-Project={up}", "-WaitMutex"]
    if name == "build_game":
        return [ubt, "Blazarshootem", "Win64", "Development", f"-Project={up}", "-WaitMutex"]
    if name == "navmesh":
        return [ed, up, "-run=ResavePackages", "-BuildNavigationData", "-AllowCommandletRendering"] + maparg + common
    if name == "lighting":
        return [ed, up, "-run=ResavePackages", "-BuildLighting", "-Quality=Preview", "-AllowCommandletRendering"] + maparg + common
    if name == "cook":
        return [ed, up, "-run=cook", "-targetplatform=Windows", "-iterate"] + (["-map=" + mp] if mp else []) + common
    if name.startswith("test:") and re.fullmatch(r"test:[A-Za-z0-9_.]+", name):
        return [
            ed,
            up,
            f"-ExecCmds=Automation RunTests {name[5:]};Quit",
            "-TestExit=Automation Test Queue Empty",
            "-NullRHI",
        ] + common
    raise ValueError("unknown preset: " + name)


def pack_context(files, errors=None, max_chars=50000):
    """Pack allowed files + optional compiler errors into a prompt-sized blob."""
    parts = []
    budget = max_chars
    if errors:
        err = errors[-8000:]
        parts.append("=== BUILD/TEST ERRORS (fix these) ===\n" + err)
        budget -= len(parts[-1])
    for path, content in files.items():
        chunk = f"=== {path} ===\n{content}"
        if len(chunk) > budget:
            chunk = chunk[: max(0, budget - 80)] + "\n...[truncated]..."
        parts.append(chunk)
        budget -= len(chunk)
        if budget < 500:
            break
    return "\n\n".join(parts)


def ask_model(lf, goal, files, errors=None, attempt=1):
    ctx = pack_context(files, errors=errors)
    prompt = (
        "You are Blazar AI, a careful Unreal Engine C++ coding agent.\n"
        f"GOAL: {goal}\n"
        f"Attempt {attempt} of {MAX_RETRIES}.\n"
        "Rules:\n"
        "- Only change the listed files.\n"
        "- Return the FULL new content of every file you change.\n"
        "- Prefer the smallest correct edit.\n"
        "- Do not invent new files.\n"
        "- Do not touch blockchain, wallet, crypto, secrets, or .env paths.\n"
        f"Current files and errors:\n{ctx}\n\n"
        'Reply with JSON only: {"plan":"<short plan>","files":{"<path>":"<full new file content>"},"summary":"<one line>"}'
    )
    body = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "format": "json",
        "keep_alive": "10m",
        "options": {"num_ctx": NUM_CTX, "temperature": 0.15},
    }
    t0 = time.time()
    data = ollama_request("/api/generate", body, timeout=MODEL_TIMEOUT)
    dur = time.time() - t0
    eval_count = data.get("eval_count") or 0
    eval_ns = data.get("eval_duration") or 0
    tps = (eval_count / (eval_ns / 1e9)) if eval_ns else 0
    log(lf, f"model: {eval_count} tokens in {dur:.1f}s ({tps:.1f} tok/s)")
    raw = data.get("response") or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def write_nightly_report(results):
    day = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(REPORTS, f"nightly-{day}.md")
    lines = [
        f"# Blazar AI nightly report — {day}",
        "",
        f"- Host: main PC",
        f"- Model: `{MODEL}`",
        f"- Jobs this pass: {len(results)}",
        "",
    ]
    for r in results:
        lines.append(f"## {r.get('id')}")
        lines.append(f"- type: {r.get('type')}")
        lines.append(f"- status: **{r.get('status')}**")
        if r.get("summary"):
            lines.append(f"- summary: {r['summary']}")
        if r.get("commit"):
            lines.append(f"- commit: `{r['commit']}` on `{r.get('branch')}`")
        if r.get("steps"):
            lines.append(f"- steps: `{json.dumps(r['steps'])}`")
        if r.get("error"):
            lines.append(f"- error: {r['error']}")
        if r.get("attempts"):
            lines.append(f"- attempts: {r['attempts']}")
        lines.append("")
    open(path, "a", encoding="utf-8").write("\n".join(lines) + "\n")
    return path


def do_preset(lf, t, res):
    for step in [t["preset"]] + t.get("tests", []):
        busy = list_busy_procs()
        if busy:
            raise RuntimeError("busy processes: " + ", ".join(busy))
        t0 = time.time()
        rc, out, err = run(lf, preset(step, PROJECT, t), PROJECT, t.get("max_minutes", 180) * 60)
        res.setdefault("steps", []).append(
            {"step": step, "rc": rc, "minutes": round((time.time() - t0) / 60, 1)}
        )
        if rc:
            raise RuntimeError(f"step {step} failed rc={rc}")
    res["status"] = "ok"


def do_ai_edit(lf, t, res, wt):
    files = {}
    for f in t["allowed_files"]:
        full = safe_rel(wt, f)
        files[f] = open(full, encoding="utf-8", errors="replace").read() if os.path.exists(full) else ""
        if len(files[f]) > 80000:
            raise ValueError("file too big for local model: " + f)

    errors = None
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        res["attempts"] = attempt
        log(lf, f"ai_edit attempt {attempt}/{MAX_RETRIES}")
        out = ask_model(lf, t["goal"], files, errors=errors, attempt=attempt)
        res["plan"] = out.get("plan", "")
        res["summary"] = out.get("summary", "")
        changed = []
        for f, content in (out.get("files") or {}).items():
            if f not in t["allowed_files"]:
                log(lf, "IGNORED disallowed file from model: " + f)
                continue
            full = safe_rel(wt, f)
            os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
            open(full, "w", encoding="utf-8", newline="\n").write(content)
            changed.append(f)
            files[f] = content
        if not changed and not t.get("tests"):
            raise RuntimeError("model returned no allowed file changes")

        test_ok = True
        for step in t.get("tests", []):
            busy = list_busy_procs()
            if busy:
                raise RuntimeError("busy processes: " + ", ".join(busy))
            rc, out_s, err_s = run(lf, preset(step, wt, t), wt, t.get("max_minutes", 120) * 60)
            res.setdefault("steps", []).append({step: rc, "attempt": attempt})
            if rc:
                test_ok = False
                last_err = f"step {step} failed rc={rc}"
                errors = (out_s or "") + "\n" + (err_s or "")
                log(lf, f"retry after failure: {last_err}")
                break
        if test_ok:
            return changed
    raise RuntimeError(last_err or "ai_edit failed after retries")


def do_task(path):
    t = json.load(open(path, encoding="utf-8-sig"))
    tid = t["id"]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", tid):
        raise ValueError("bad id")
    lf = open(os.path.join(DONE, tid + ".log"), "w", encoding="utf-8")
    res = {
        "id": tid,
        "type": t["type"],
        "status": "fail",
        "started": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model": MODEL,
    }
    used_model = False
    try:
        if t["type"] == "preset":
            do_preset(lf, t, res)
            return res

        branch, wt = "blazar-ai/" + tid, os.path.join(WT, tid)
        if not os.path.isdir(wt):
            rc, _, _ = run(
                lf,
                [GIT, "worktree", "add", "-b", branch, wt, t.get("base", "HEAD")],
                PROJECT,
                600,
            )
            if rc:
                raise RuntimeError("worktree add failed")
        res.update(branch=branch, worktree=wt)

        if t["type"] == "append_note":
            f = t["allowed_files"][0]
            full = safe_rel(wt, f)
            os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
            open(full, "a", encoding="utf-8").write("\n" + t["text"] + "\n")
            changed = [f]
        elif t["type"] == "ai_edit":
            used_model = True
            changed = do_ai_edit(lf, t, res, wt)
        else:
            raise ValueError("unknown type")

        if changed:
            run(lf, [GIT, "add", "--"] + changed, wt, 120)
            msg = f"[blazar-ai] {tid}: {t.get('goal', t['type'])}"[:200]
            rc, _, _ = run(
                lf,
                [
                    GIT,
                    "-c",
                    "user.name=Blazar AI",
                    "-c",
                    "user.email=blazar-ai@local",
                    "commit",
                    "-m",
                    msg,
                ],
                wt,
                120,
            )
            if rc == 0:
                res["commit"] = subprocess.run(
                    [GIT, "rev-parse", "--short", "HEAD"],
                    cwd=wt,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
        res["changed"] = changed
        res["status"] = "ok"
    except Exception as e:
        res["error"] = str(e)
        log(lf, traceback.format_exc())
    finally:
        if used_model:
            unload_model(lf)
        res["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        json.dump(res, open(os.path.join(DONE, tid + ".result.json"), "w"), indent=2)
        lf.close()
    return res


def main():
    lock = os.path.join(HOME, "runner.lock")
    if os.path.exists(lock) and time.time() - os.path.getmtime(lock) < 6 * 3600:
        print("already running")
        return
    if os.path.exists(os.path.join(HOME, "paused.flag")):
        print("paused")
        return
    # Manual-only: start.bat / `python runner.py` (optional --require-idle).
    # No overnight window and no scheduled task.
    busy = list_busy_procs()
    if busy:
        print("busy processes:", ", ".join(busy))
        return
    if "--require-idle" in sys.argv and not pc_idle_enough():
        print(f"PC not idle (cpu >= {IDLE_CPU_PCT}%)")
        return

    open(lock, "w", encoding="utf-8").write(str(os.getpid()))
    results = []
    try:
        for name in sorted(os.listdir(Q)):
            if not name.endswith(".json"):
                continue
            if list_busy_procs():
                print("stopping: Unreal/game started mid-queue")
                break
            dst = os.path.join(RUN, name)
            shutil.move(os.path.join(Q, name), dst)
            try:
                r = do_task(dst)
                results.append(r)
                print(json.dumps(r))
            except Exception as e:
                print("task error", name, e)
                results.append({"id": name, "status": "fail", "error": str(e)})
            finally:
                if os.path.exists(dst):
                    shutil.move(dst, os.path.join(DONE, name))
        if results:
            report = write_nightly_report(results)
            print("report:", report)
    finally:
        unload_model()
        if os.path.exists(lock):
            os.remove(lock)


if __name__ == "__main__":
    main()
