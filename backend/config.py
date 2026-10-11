"""
config.py — Centralised configuration for DocGlance backend.
All tuneable parameters live here; modules import from this file.
Override any value via environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
UPLOAD_DIR: Path = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ── Model configuration (100% Free, Open-Source & Offline) ───────────────────
# Supports Qwen2.5 series:
#   - Qwen/Qwen2.5-0.5B-Instruct (~900MB, lightning fast on CPU, 32k context)
#   - Qwen/Qwen2.5-1.5B-Instruct (~3GB, higher reasoning capability, 32k context)
CHAT_MODEL_NAME: str = os.getenv("CHAT_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")

# ── Whole-Document Context Budget ─────────────────────────────────────────────
MAX_DOC_TOKENS_FOR_CONTEXT: int = int(os.getenv("MAX_DOC_TOKENS", "16384"))
CHAT_MAX_NEW_TOKENS: int = int(os.getenv("MAX_NEW_TOKENS", "1500"))
CHAT_TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.3"))
CHAT_TOP_P: float = float(os.getenv("TOP_P", "0.90"))
CHAT_REPETITION_PENALTY: float = float(os.getenv("REPETITION_PENALTY", "1.1"))

# ── Gemini Cloud API Configuration (Optional) ──────────────────────────────
# If GEMINI_API_KEY is provided via env or UI settings, uses Google Gemini Cloud LLM.
# If not provided, falls back to 100% Free Offline Local Neural/Macro Engine.
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY", None)
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── Server ───────────────────────────────────────────────────────────────────
API_HOST: str = os.getenv("HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("PORT", "4000"))

ALLOWED_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3100",
    "http://127.0.0.1:3100",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
    "http://localhost:4000",
    "http://127.0.0.1:4000",
]

# ── Universal Document Support ───────────────────────────────────────────────
# Microsoft 365 + Google Workspace + PDF + Data + Web + Text ecosystem
ALLOWED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".pdf",
        ".docx",
        ".doc",
        ".xlsx",
        ".xls",
        ".csv",
        ".tsv",
        ".pptx",
        ".ppt",
        ".html",
        ".htm",
        ".txt",
        ".md",
        ".markdown",
        ".rst",
        ".json",
        ".yaml",
        ".yml",
        ".xml",
    }
)
