"""
main.py — Gemini Doc FastAPI Application.

Full-Document Conversational Intelligence strictly grounded in your document.
Supports:
  - Google Gemini 2.0 / 1.5 Flash (via Gemini API key)
  - 100% Offline Local Neural Engine (Qwen2.5) & High-Fidelity Macro Synthesizer
  - Real-time token streaming with SSE
  - Contextual follow-up suggestions
  - Google Search & web context recommendations
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

import config
from core.chat_engine import ChatEngine, get_model_status, _load_model
from core.document_analyzer import DocumentProfile, WholeDocumentAnalyzer
from core.document_parser import parse_any_document

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("geminidoc.main")

# ── In-Memory Session State ──────────────────────────────────────────────────
_analyzer: WholeDocumentAnalyzer = WholeDocumentAnalyzer()
_chat_engine: ChatEngine = ChatEngine()

_active_document_profile: DocumentProfile | None = None
_active_document_text: str | None = None


# ── Lifespan (Prewarm model in background thread) ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    global _active_document_profile, _active_document_text
    logger.info("Booting Gemini Doc Neural Engine…")
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Restore active document if previously cached
    profile_cache = config.UPLOAD_DIR / "active_profile.json"
    text_cache = config.UPLOAD_DIR / "active_text.txt"
    if profile_cache.exists() and text_cache.exists():
        try:
            with open(profile_cache, "r", encoding="utf-8") as f:
                _active_document_profile = DocumentProfile.from_dict(json.load(f))
            with open(text_cache, "r", encoding="utf-8") as f:
                _active_document_text = f.read()
            logger.info("Restored active document from cache: %s", _active_document_profile.filename)
        except Exception as exc:
            logger.warning("Failed to restore cached document: %s", exc)

    # Prewarm local model asynchronously in background thread
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _load_model)

    yield
    logger.info("Shutting down Gemini Doc")


# ── App Definition ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Gemini Doc API",
    description="Full-Document Conversational Intelligence strictly grounded in your document",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic Request & Response Schemas ───────────────────────────────────────
class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = False
    api_key: str | None = None


class GoogleContext(BaseModel):
    queries: list[str] = Field(default_factory=list)
    related_topics: list[str] = Field(default_factory=list)
    primary_concept: str = ""
    overview: str = ""


class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    document: str | None = None
    latency_ms: float = 0.0
    suggestions: list[str] = Field(default_factory=list)
    google_context: GoogleContext | None = None


class DocumentUploadResponse(BaseModel):
    filename: str
    file_type: str
    word_count: int
    char_count: int
    estimated_read_time_mins: int
    key_concepts: list[str]
    executive_summary: str
    section_map: list[dict[str, Any]]
    message: str


class HealthResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    status: str
    app: str
    version: str
    model_name: str
    model_status: str
    has_gemini_key: bool
    active_document: str | None
    allowed_file_types: list[str]


class ConfigResponse(BaseModel):
    has_gemini_key: bool
    gemini_model: str
    local_model: str
    local_model_status: str


class ConfigUpdateRequest(BaseModel):
    gemini_api_key: str | None = None
    gemini_model: str | None = None


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app="Gemini Doc",
        version="2.0.0",
        model_name=config.CHAT_MODEL_NAME,
        model_status=get_model_status(),
        has_gemini_key=bool(config.GEMINI_API_KEY),
        active_document=_active_document_profile.filename if _active_document_profile else None,
        allowed_file_types=sorted(config.ALLOWED_EXTENSIONS),
    )


@app.get("/api/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    return ConfigResponse(
        has_gemini_key=bool(config.GEMINI_API_KEY),
        gemini_model=config.GEMINI_MODEL,
        local_model=config.CHAT_MODEL_NAME,
        local_model_status=get_model_status(),
    )


@app.post("/api/config")
async def update_config(req: ConfigUpdateRequest) -> dict[str, str]:
    if req.gemini_api_key is not None:
        config.GEMINI_API_KEY = req.gemini_api_key.strip() or None
    if req.gemini_model is not None:
        config.GEMINI_MODEL = req.gemini_model.strip() or "gemini-2.0-flash"
    return {"message": "Configuration updated successfully."}


@app.get("/api/document/active")
async def get_active_document() -> dict[str, Any] | None:
    if not _active_document_profile:
        return None
    return _active_document_profile.to_dict()


@app.delete("/api/document")
async def clear_active_document() -> dict[str, str]:
    global _active_document_profile, _active_document_text
    _active_document_profile = None
    _active_document_text = None
    profile_cache = config.UPLOAD_DIR / "active_profile.json"
    text_cache = config.UPLOAD_DIR / "active_text.txt"
    if profile_cache.exists():
        profile_cache.unlink()
    if text_cache.exists():
        text_cache.unlink()
    return {"message": "Active document unloaded successfully."}


@app.post("/api/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)) -> DocumentUploadResponse:
    global _active_document_profile, _active_document_text

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = Path(file.filename).suffix.lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported format '{ext}'. Gemini Doc supports: {sorted(config.ALLOWED_EXTENSIONS)}",
        )

    logger.info("Ingesting document: %s (%s)", file.filename, ext)
    file_bytes = await file.read()

    # Save local copy in uploads directory
    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(file.filename).name}"
    (config.UPLOAD_DIR / safe_name).write_bytes(file_bytes)

    loop = asyncio.get_event_loop()

    # Step 1: Universal Document Parsing
    try:
        parsed = await loop.run_in_executor(
            None,
            partial(parse_any_document, file_bytes=file_bytes, filename=file.filename),
        )
    except Exception as exc:
        logger.exception("Failed to parse %s", file.filename)
        raise HTTPException(status_code=422, detail=f"Document parsing failed: {exc}") from exc

    if not parsed.raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "This document contains no extractable digital text (e.g. image-only scan or rasterized presentation). "
                "Please upload a searchable PDF or the original PowerPoint (.pptx) / Word (.docx) file."
            ),
        )

    # Step 2: Whole-Document Structural & Semantic NLP Analysis
    try:
        profile = await loop.run_in_executor(
            None,
            partial(_analyzer.analyze, parsed=parsed),
        )
    except Exception as exc:
        logger.exception("Whole-document analysis failed for %s", file.filename)
        raise HTTPException(status_code=500, detail=f"Document analysis failed: {exc}") from exc

    # Set as active working document
    _active_document_profile = profile
    _active_document_text = parsed.raw_text

    # Persist to disk for recovery across server restarts
    try:
        profile_cache = config.UPLOAD_DIR / "active_profile.json"
        text_cache = config.UPLOAD_DIR / "active_text.txt"
        with open(profile_cache, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f)
        with open(text_cache, "w", encoding="utf-8") as f:
            f.write(parsed.raw_text)
    except Exception as exc:
        logger.warning("Could not persist active document cache: %s", exc)

    logger.info(
        "Successfully analyzed '%s': %d words, %d sections, %d key concepts",
        profile.filename,
        profile.word_count,
        len(profile.section_map),
        len(profile.key_concepts),
    )

    return DocumentUploadResponse(
        filename=profile.filename,
        file_type=profile.file_type,
        word_count=profile.word_count,
        char_count=profile.char_count,
        estimated_read_time_mins=profile.estimated_read_time_mins,
        key_concepts=profile.key_concepts,
        executive_summary=profile.executive_summary,
        section_map=profile.section_map,
        message=f"Document '{profile.filename}' analyzed successfully. Ready for conversation!",
    )


@app.post("/api/sample", response_model=DocumentUploadResponse)
async def load_sample_document() -> DocumentUploadResponse:
    global _active_document_profile, _active_document_text
    sample_path = Path(__file__).parent.parent / "sample_jwst.txt"
    if not sample_path.exists():
        sample_path = Path(__file__).parent / "sample_jwst.txt"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample file sample_jwst.txt not found.")

    file_bytes = sample_path.read_bytes()
    parsed = parse_any_document(file_bytes=file_bytes, filename="sample_jwst.txt")
    profile = _analyzer.analyze(parsed=parsed)

    _active_document_profile = profile
    _active_document_text = parsed.raw_text

    try:
        profile_cache = config.UPLOAD_DIR / "active_profile.json"
        text_cache = config.UPLOAD_DIR / "active_text.txt"
        with open(profile_cache, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f)
        with open(text_cache, "w", encoding="utf-8") as f:
            f.write(parsed.raw_text)
    except Exception:
        pass

    return DocumentUploadResponse(
        filename=profile.filename,
        file_type=profile.file_type,
        word_count=profile.word_count,
        char_count=profile.char_count,
        estimated_read_time_mins=profile.estimated_read_time_mins,
        key_concepts=profile.key_concepts,
        executive_summary=profile.executive_summary,
        section_map=profile.section_map,
        message="Sample document loaded successfully!",
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> Any:
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty.")

    msg_dicts = [{"role": m.role, "content": m.content} for m in request.messages]
    last_query = request.messages[-1].content

    if request.stream:
        # Server-Sent Events (SSE) streaming
        def sse_generator():
            accumulated: list[str] = []
            try:
                for token in _chat_engine.chat_stream(
                    messages=msg_dicts,
                    doc_profile=_active_document_profile,
                    full_text=_active_document_text,
                    api_key=request.api_key,
                ):
                    accumulated.append(token)
                    yield f"data: {token}\n\n"

                # Send follow-up suggestions and Google context as metadata before DONE
                full_reply = "".join(accumulated)
                suggestions = _chat_engine.generate_followup_suggestions(
                    last_query, _active_document_profile, full_reply
                )
                google_context = _chat_engine.generate_google_context(
                    last_query, _active_document_profile
                )
                meta_json = json.dumps({"suggestions": suggestions, "google_context": google_context})
                yield f"data: [META]: {meta_json}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as exc:
                logger.exception("Streaming generation error")
                yield f"data: [ERROR: {exc}]\n\n"

        return StreamingResponse(sse_generator(), media_type="text/event-stream")

    # Synchronous multi-turn generation (runs in thread pool)
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None,
            partial(
                _chat_engine.chat_sync,
                messages=msg_dicts,
                doc_profile=_active_document_profile,
                full_text=_active_document_text,
                api_key=request.api_key,
            ),
        )
    except Exception as exc:
        logger.exception("Chat generation failed")
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc

    return ChatResponse(
        role="assistant",
        content=result["content"],
        document=result.get("document"),
        latency_ms=result.get("latency_ms", 0.0),
        suggestions=result.get("suggestions", []),
        google_context=result.get("google_context"),
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.API_HOST, port=config.API_PORT, reload=True)
