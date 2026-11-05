# Blazar AI job runner (main PC)

Manual only. Double-click `start.bat` (or run `start.ps1` / `python runner.py`) when you want it to work. It drains `queue\*.json`, writes results under `done\`, appends `reports\nightly-YYYY-MM-DD.md`, unloads the Ollama model, and exits.

There is **no scheduled task** and **no overnight window**. Create `paused.flag` in this folder to block starts. The runner also refuses to start (and stops mid-queue) if Unreal Editor or the game is running, so it never fights the GPU with you.

## Model

Default: `qwen2.5-coder:14b` on the RTX 2070 SUPER (8 GB VRAM) with CPU offload as needed. Change `model` in `config.json` if you pull another one.

## Job types

Drop JSON files into `queue\` (processed in filename order):

| type | where it runs | commits? |
|------|---------------|----------|
| `preset` | main project | no |
| `ai_edit` | worktree on `blazar-ai/<id>` | yes, local only, never push |
| `append_note` | worktree on `blazar-ai/<id>` | yes, local only |

Presets: `build`, `build_game`, `navmesh`, `lighting`, `cook`, `test:<Name>`. Optional `"map"` must be a `/Game/...` path.

`ai_edit` does plan → edit → build/test → retry (up to `max_retries`, default 3), feeding compiler errors back into the prompt.

## Examples

See `examples\`. Build sessions can drop jobs into `queue\` any time; nothing runs until you start the runner.

## Safety

- Blocked paths: chain/wallet/web3/solana/polygon/blockchain/rpc/crypto/token/secret/.env, plus Engine/Binaries/Intermediate/Saved/DerivedDataCache/.git
- Never pushes. Never runs arbitrary shell.
- Unloads the model (`keep_alive=0` + `ollama stop`) when finished.
