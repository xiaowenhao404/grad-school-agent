---
name: setup-environment
description: One-shot environment bootstrapper for Grad-School-Agent. Verifies Python, runs `uv sync`, scaffolds `.env` from `.env.example`, prompts for DeepSeek API key, ensures `data/` directory tree, initializes SQLite + Chroma, runs an import-time verification, and (optionally) launches Streamlit. Use when user says "setup environment", "一键配置", "初始化环境", "install deps", "搭建环境", or whenever a fresh checkout needs to be made runnable.
---

# Setup Environment — Grad-School-Agent

One trigger completes **check Python → uv sync → scaffold .env → init data dir → init DB + Chroma → verify → (optional) launch Streamlit**.

Optional modifiers:
- `--run` after setup, also start `streamlit run app.py`
- `--force` recreate `.venv` from scratch via `uv sync --reinstall`
- `--no-verify` skip the import smoke test

---

## Pipeline

```
Check Python (3.10–3.12)
        ↓
Ensure uv is installed
        ↓
uv sync   (creates/updates .venv, installs from pyproject.toml)
        ↓
Ensure .env (copy from .env.example if missing, then prompt for DeepSeek/Qwen keys)
        ↓
Ensure data/ tree (data/chroma, data/raw_docs/{schools,teachers,internal}, data/seed)
        ↓
Initialize DB + Chroma   (`uv run python -m src.db.init_db`)
        ↓
Verify imports (langchain, langgraph, chromadb, streamlit, sqlalchemy, openai)
        ↓
[optional] uv run streamlit run app.py
```

---

## Step-by-Step

### 1. Check Python

Required: **Python 3.10, 3.11, or 3.12** (3.13+ has known LangChain 0.3.x compatibility issues).

```powershell
python --version
```

If missing, install Python 3.12 via `winget install --id Python.Python.3.12 -e` (Windows) or your package manager.

### 2. Ensure `uv` is installed

```powershell
uv --version
# If missing:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Sync dependencies

```powershell
uv sync
```

`uv` will read `pyproject.toml`, create `.venv` if absent, and install all dependencies pinned by `uv.lock`.

### 4. Fill `.env`

Copy template and edit:

```powershell
Copy-Item .env.example .env
```

Required for Grad-School-Agent:

| Key | Required | Notes |
|-----|----------|-------|
| `LLM_API_KEY` | ✅ | DeepSeek API key from <https://platform.deepseek.com/> |
| `LLM_BASE_URL` | ✅ | Default `https://api.deepseek.com/v1` |
| `LLM_MODEL` | ✅ | Default `deepseek-chat` |
| `EMBEDDING_PROVIDER` | ✅ | `qwen` (recommended) or `local` |
| `EMBEDDING_API_KEY` | If non-local | Qwen / DashScope key |
| `EMBEDDING_BASE_URL` | If non-local | OpenAI-compatible embedding URL |
| `EMBEDDING_MODEL` | If non-local | e.g. `text-embedding-v3` |
| `EXCHANGE_RATE_API_KEY` | ⚠ optional | Currency tool external API; falls back to static rates if absent |
| `OPENWEATHER_API_KEY` | ⚠ optional | Weather tool; gracefully degrades if absent |

If any required value still equals `your_..._here`, **pause and ask the user to fill it**. Never commit a populated `.env`.

### 5. Ensure data tree

```powershell
New-Item -ItemType Directory -Force -Path data\chroma | Out-Null
New-Item -ItemType Directory -Force -Path data\raw_docs\schools | Out-Null
New-Item -ItemType Directory -Force -Path data\raw_docs\teachers | Out-Null
New-Item -ItemType Directory -Force -Path data\raw_docs\internal | Out-Null
New-Item -ItemType Directory -Force -Path data\seed | Out-Null
```

### 6. Initialize DB + Chroma

```powershell
uv run python -m src.db.init_db
```

This creates `data/grad_school.db` with all 9 tables, and 3 empty Chroma collections (`schools`, `teachers`, `internal_docs`). If `data/seed/*.json` exists, seed data is imported.

### 7. Verify

```powershell
uv run python -c "import langchain, langgraph, chromadb, streamlit, sqlalchemy, openai; print('OK')"
```

### 8. (Optional) Launch

```powershell
uv run streamlit run app.py
```

Open <http://localhost:8501> in browser.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `uv: command not found` | Install uv (see Step 2). |
| `Python 3.13` chosen by uv | Set `UV_PYTHON=3.12` env var or install Python 3.12. |
| `chromadb` install fails on Windows | Ensure Visual C++ Build Tools installed; retry after `uv sync --reinstall`. |
| `DeepSeek 401 Unauthorized` | Re-check `LLM_API_KEY`, ensure no trailing whitespace. |
| Port 8501 already in use | `streamlit run app.py --server.port 8502` |
| `ModuleNotFoundError: src.*` | Run from project root, or activate `.venv` first. |

---

## Files in this skill

```
.claude/skills/setup-environment/
└── SKILL.md   ← this file
```

`.env.example` lives at project root and is the canonical template.
