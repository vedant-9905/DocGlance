"""
chat_engine.py — Conversational Multi-Turn LLM Engine for Gemini Doc.

Provides Google Gemini / ChatGPT style multi-turn chat strictly grounded
in the uploaded document.
Features:
  - Google Gemini 2.0 / 1.5 Flash API support (when API key provided)
  - 100% Offline Local Neural Model (Qwen2.5) support
  - High-Fidelity Macro Document Synthesis Engine (deep, structured, detailed offline analysis)
  - Strict document grounding (no hallucinations outside document)
  - Real-time streaming generation
  - Dynamic follow-up suggestion generation
  - Google Search & web context suggestions
"""

from __future__ import annotations

import collections
import json
import logging
import os
import re
import threading
import time
from typing import Any, Generator

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TextIteratorStreamer,
)

import config
from config import (
    CHAT_MAX_NEW_TOKENS,
    CHAT_MODEL_NAME,
    CHAT_REPETITION_PENALTY,
    CHAT_TEMPERATURE,
    CHAT_TOP_P,
    MAX_DOC_TOKENS_FOR_CONTEXT,
)
from core.document_analyzer import DocumentProfile, _STOPWORDS

logger = logging.getLogger(__name__)

# Try importing google-generativeai
try:
    import google.generativeai as genai
    _HAS_GENAI = True
except ImportError:
    genai = None  # type: ignore
    _HAS_GENAI = False

_model: Any = None
_tokenizer: Any = None
_model_lock = threading.Lock()
_model_status: str = "uninitialized"


def _get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load_model() -> tuple[Any, Any]:
    global _model, _tokenizer, _model_status
    if _model is None:
        with _model_lock:
            if _model is None:
                logger.info("Loading Local Conversational LLM: %s", CHAT_MODEL_NAME)
                _model_status = "loading"
                try:
                    tokenizer = AutoTokenizer.from_pretrained(
                        CHAT_MODEL_NAME,
                        trust_remote_code=True,
                    )
                    model = AutoModelForCausalLM.from_pretrained(
                        CHAT_MODEL_NAME,
                        torch_dtype=torch.float32,
                        low_cpu_mem_usage=True,
                        trust_remote_code=True,
                    )
                    model.eval()
                    _tokenizer = tokenizer
                    _model = model
                    _model_status = "ready"
                    logger.info("Conversational LLM ready on %s ✓", _get_device())
                except Exception as exc:
                    _model_status = f"error: {exc}"
                    logger.exception("Failed to load local LLM %s", CHAT_MODEL_NAME)
                    raise
    return _model, _tokenizer


def get_model_status() -> str:
    return _model_status


class ChatEngine:
    """
    Manages conversational document sessions.
    Grounds multi-turn conversations strictly in the uploaded document.
    """

    def __init__(self) -> None:
        pass

    def build_system_prompt(self, doc_profile: DocumentProfile | None, full_text: str | None) -> str:
        """
        Constructs the whole-document system prompt that grounds the LLM
        strictly in the uploaded document.
        """
        if not doc_profile or not full_text:
            return (
                "You are Gemini Doc, an advanced, articulate conversational document intelligence assistant. "
                "No document is currently uploaded. Politely prompt the user to upload a file (PDF, Word, Excel, PPTX, CSV) "
                "so you can analyze it as a whole."
            )

        max_words = int(MAX_DOC_TOKENS_FOR_CONTEXT * 0.75)
        words = full_text.split()
        if len(words) > max_words:
            doc_context = " ".join(words[:max_words]) + "\n\n[... Note: Document continues; executive summary covers overall scope ...]"
        else:
            doc_context = full_text

        return f"""You are Gemini Doc, an advanced document intelligence assistant built with the conversational depth and clarity of Google Gemini.
You are strictly and solely grounded in the user's uploaded document.

=== DOCUMENT PASSPORT ===
- Filename: {doc_profile.filename} ({doc_profile.file_type})
- Total Words: {doc_profile.word_count:,} words
- Estimated Reading Time: {doc_profile.estimated_read_time_mins} minutes
- Key Concepts: {', '.join(doc_profile.key_concepts)}
- Executive Macro-Summary: {doc_profile.executive_summary}

=== FULL DOCUMENT CONTENT ===
{doc_context}
=============================

BEHAVIORAL INSTRUCTIONS:
1. Provide comprehensive, deeply insightful, articulate, and well-structured responses. Explain details thoroughly rather than giving brief summaries.
2. Analyze the document AS A WHOLE. Connect overarching themes, compare different sections, synthesize data, and cite specific sections, headings, or metrics from the document.
3. If the user asks for summaries, explanations, data, or breakdowns, organize your response with clear Markdown formatting:
   - Use bold titles and descriptive headers (`###`).
   - Use bullet points (`-`) and numbered steps for structured takeaways.
   - Use Markdown comparison tables when data, numbers, or comparisons are relevant.
   - Use blockquotes (`>`) for direct excerpts and quotes from the document.
4. STRICT GROUNDING: Do NOT hallucinate facts outside the provided document. If information is not mentioned in the document, explicitly clarify: "This information is not mentioned in {doc_profile.filename}."
5. At the end of each response, recommend relevant follow-up inquiries that can be explored within the document.
"""

    def generate_followup_suggestions(
        self,
        query: str,
        doc_profile: DocumentProfile | None,
        answer: str = "",
    ) -> list[str]:
        """
        Generates 3-4 smart, context-aware follow-up suggestion chips
        based on the document's structure and the user's query.
        """
        if not doc_profile:
            return [
                "Upload a PDF or Word document to begin",
                "Load sample document to test",
                "What file formats are supported?",
            ]

        suggestions: list[str] = []
        q_lower = query.lower()

        # Suggest based on sections
        sections = doc_profile.section_map
        if sections and len(sections) > 1:
            # Pick a section not mentioned in current query
            unvisited = [s["title"] for s in sections if s["title"].lower() not in q_lower and len(s["title"].strip()) > 3]
            if unvisited:
                suggestions.append(f"Explain the '{unvisited[0]}' section in detail")
            if len(unvisited) > 1:
                suggestions.append(f"What are the key takeaways from '{unvisited[1]}'?")

        # Suggest based on key concepts
        concepts = doc_profile.key_concepts
        if concepts:
            unused_concepts = [c for c in concepts if c.lower() not in q_lower]
            if unused_concepts:
                suggestions.append(f"How does the document define '{unused_concepts[0]}'?")
            if len(unused_concepts) > 1 and len(suggestions) < 3:
                suggestions.append(f"Explore the role of '{unused_concepts[1]}' in this context")

        # General high-value document queries
        standard_prompts = [
            f"Extract all metrics, numbers, and data points from {doc_profile.filename}",
            "What are the primary risks, limitations, or future work mentioned?",
            "Create a structured comparison table of the main findings",
            "What are the actionable conclusions and recommendations?",
        ]
        for p in standard_prompts:
            if len(suggestions) >= 4:
                break
            if p not in suggestions:
                suggestions.append(p)

        return suggestions[:4]

    def generate_google_context(
        self,
        query: str,
        doc_profile: DocumentProfile | None,
    ) -> dict[str, Any]:
        """
        Generates Google Search query suggestions and external contextual relevance
        connected to the document's concepts.
        """
        if not doc_profile:
            return {"queries": [], "related_topics": [], "overview": ""}

        concepts = doc_profile.key_concepts[:5]
        q_words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", query.lower()) if w not in _STOPWORDS]
        matched_concept = concepts[0] if concepts else "Document Analysis"
        for c in concepts:
            if c.lower() in query.lower():
                matched_concept = c
                break

        search_queries = [
            f"{matched_concept} state of the art 2026",
            f"{matched_concept} industry best practices & standards",
            f"{concepts[1] if len(concepts) > 1 else matched_concept} latest research",
        ]

        overview = (
            f"In broader industry and academic research, '{matched_concept}' connects to active developments in "
            f"{', '.join(concepts[:3])}. External search can provide real-world benchmarks, competing frameworks, "
            f"and updated regulatory or empirical standards."
        )

        return {
            "queries": search_queries,
            "related_topics": concepts,
            "primary_concept": matched_concept,
            "overview": overview,
        }

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        doc_profile: DocumentProfile | None,
        full_text: str | None,
        api_key: str | None = None,
    ) -> Generator[str, None, None]:
        """
        Streaming generator supporting Google Gemini Cloud API and Local fallback.
        """
        global _model, _tokenizer

        if not doc_profile or not full_text:
            yield "No document is currently loaded. Please upload a PDF, Word, Excel, PowerPoint, CSV, or Text file to begin exploring!"
            return

        effective_key = api_key or config.GEMINI_API_KEY
        system_prompt = self.build_system_prompt(doc_profile, full_text)
        user_query = messages[-1]["content"] if messages else ""

        # Option A: Google Gemini Cloud API
        if effective_key and _HAS_GENAI:
            try:
                genai.configure(api_key=effective_key)
                gemini_model = genai.GenerativeModel(
                    model_name=config.GEMINI_MODEL,
                    system_instruction=system_prompt,
                )

                # Format chat history for Gemini
                contents = []
                for m in messages:
                    role = "user" if m["role"] == "user" else "model"
                    contents.append({"role": role, "parts": [m["content"]]})

                response = gemini_model.generate_content(
                    contents,
                    stream=True,
                    generation_config=genai.types.GenerationConfig(
                        temperature=config.CHAT_TEMPERATURE,
                        max_output_tokens=config.CHAT_MAX_NEW_TOKENS,
                    ),
                )
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as exc:
                logger.warning("Gemini Cloud API call failed (%s); falling back to local engine", exc)

        # Check if macro query (summary, overview, key points, structure, etc.)
        q_lower = user_query.lower()
        is_macro_query = any(
            w in q_lower
            for w in [
                "about", "summarize", "summary", "overview", "conclusion",
                "main finding", "core argument", "thesis", "structure",
                "sections", "table", "proposal", "what is this", "key finding",
                "takeaway", "metric", "number", "data", "figure"
            ]
        )

        # If no Gemini API key and query is macro-oriented, serve instant Macro Synthesis
        if not effective_key and is_macro_query:
            fallback_text = self._nlp_macro_fallback(messages, doc_profile, full_text)
            words = fallback_text.split(" ")
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
            return

        # Option B: Local Generative Neural Model (Qwen2.5) if running on CUDA GPU
        if _get_device() == "cuda" and _model is not None and _tokenizer is not None:
            try:
                model = _model
                tokenizer = _tokenizer

                max_words = int(MAX_DOC_TOKENS_FOR_CONTEXT * 0.75)
                words = full_text.split()
                compact_context = " ".join(words[:max_words])

                compact_system = (
                    f"You are Gemini Doc, grounded strictly in '{doc_profile.filename}'.\n"
                    f"Summary: {doc_profile.executive_summary}\n"
                    f"Content Excerpt:\n{compact_context}\n\n"
                    f"Answer the user's question clearly, thoroughly, and citing facts from above."
                )

                chat_history = [{"role": "system", "content": compact_system}]
                for m in messages[-4:]:
                    chat_history.append({"role": m["role"], "content": m["content"]})

                prompt_text = tokenizer.apply_chat_template(
                    chat_history,
                    tokenize=False,
                    add_generation_prompt=True,
                )

                inputs = tokenizer([prompt_text], return_tensors="pt").to("cuda")
                streamer = TextIteratorStreamer(
                    tokenizer,
                    timeout=30.0,
                    skip_prompt=True,
                    skip_special_tokens=True,
                )

                local_tokens = min(CHAT_MAX_NEW_TOKENS, 600)
                generation_kwargs = dict(
                    **inputs,
                    streamer=streamer,
                    max_new_tokens=local_tokens,
                    temperature=CHAT_TEMPERATURE,
                    top_p=CHAT_TOP_P,
                    repetition_penalty=CHAT_REPETITION_PENALTY,
                    do_sample=True,
                )

                def _run_gen():
                    with torch.inference_mode():
                        model.generate(**generation_kwargs)

                thread = threading.Thread(target=_run_gen)
                thread.start()

                for new_text in streamer:
                    yield new_text

                thread.join()
                return
            except Exception as exc:
                logger.warning("Local GPU neural generation error (%s); falling back to macro synthesis", exc)

        # Option C: High-Fidelity Macro Document Synthesis Engine (Instant, Offline)
        fallback_text = self._nlp_macro_fallback(messages, doc_profile, full_text)
        words = fallback_text.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")

    def chat_sync(
        self,
        messages: list[dict[str, str]],
        doc_profile: DocumentProfile | None,
        full_text: str | None,
        api_key: str | None = None,
    ) -> dict[str, Any]:
        """
        Synchronous full response generation with suggestions and Google search context.
        """
        t0 = time.perf_counter()
        user_query = messages[-1]["content"] if messages else ""

        try:
            tokens = list(self.chat_stream(messages, doc_profile, full_text, api_key=api_key))
            answer = "".join(tokens).strip()
        except Exception as exc:
            logger.warning("Generative chat error (%s); using macro synthesis", exc)
            answer = self._nlp_macro_fallback(messages, doc_profile, full_text)

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        suggestions = self.generate_followup_suggestions(user_query, doc_profile, answer)
        google_context = self.generate_google_context(user_query, doc_profile)

        return {
            "role": "assistant",
            "content": answer,
            "document": doc_profile.filename if doc_profile else None,
            "latency_ms": latency_ms,
            "suggestions": suggestions,
            "google_context": google_context,
        }

    def _nlp_macro_fallback(
        self,
        messages: list[dict[str, str]],
        doc_profile: DocumentProfile | None,
        full_text: str | None,
    ) -> str:
        """
        Generates deeply detailed, articulate, well-structured Gemini-grade answers
        based strictly on the whole document.
        """
        if not doc_profile or not full_text:
            return "Please upload a document (PDF, Word, Excel, PPTX, or Text) to begin the conversational analysis."

        user_query = messages[-1]["content"].lower() if messages else ""
        raw_query = messages[-1]["content"] if messages else ""

        # 1. Executive Summary & Overview Query
        is_summary_query = any(
            w in user_query
            for w in [
                "about", "summarize", "summary", "overview", "what is this", "main point",
                "core argument", "thesis", "takeaway", "tl;dr", "explain this document"
            ]
        )
        if is_summary_query:
            sections_table = "| Section | Focus & Details | Scope |\n| :--- | :--- | :--- |\n"
            for s in doc_profile.section_map[:8]:
                preview_clean = s['preview'].replace("|", "-")
                sections_table += f"| **{s['title']}** | {preview_clean} | {s['word_count']} words |\n"

            concepts_pills = ", ".join(f"`{c}`" for c in doc_profile.key_concepts)
            return (
                f"### Executive Synthesis & Whole-Document Overview\n\n"
                f"**Document**: `{doc_profile.filename}` ({doc_profile.file_type})\n"
                f"**Scope**: {doc_profile.word_count:,} words across {len(doc_profile.section_map)} structural sections (~{doc_profile.estimated_read_time_mins} min estimated read time).\n\n"
                f"#### 1. Core Thesis & Executive Spine\n"
                f"> {doc_profile.executive_summary}\n\n"
                f"#### 2. Key Conceptual Domains\n"
                f"The document centers around the following dominant subject areas:\n"
                f"{concepts_pills}\n\n"
                f"#### 3. Structural Section-by-Section Breakdown\n"
                f"{sections_table}\n\n"
                f"#### 4. Grounded Synthesis & Insights\n"
                f"This document presents a structured discussion on {', '.join(doc_profile.key_concepts[:3])}. "
                f"Each section builds upon the core thesis with dedicated empirical, technical, or strategic arguments.\n\n"
                f"Would you like me to dive deeper into any specific section, extract all numerical metrics, or compare arguments?"
            )

        # 2. Metrics, Data, Numbers, and Tables Query
        is_metrics_query = any(
            w in user_query
            for w in ["metric", "number", "statistic", "data", "figure", "table", "percentage", "amount", "cost", "date", "quantity"]
        )
        if is_metrics_query:
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", full_text) if len(s.strip()) > 15]
            # Find sentences containing digits or percentages or currencies
            metric_sents = [s for s in sentences if re.search(r"\b\d+([.,]\d+)?%?|\$\d+", s)]
            if metric_sents:
                metrics_list = "\n".join(f"- **Data Point**: {s}" for s in metric_sents[:8])
                return (
                    f"### Quantitative Metrics & Data Points in `{doc_profile.filename}`\n\n"
                    f"Below are the primary numerical and statistical references extracted directly from the document:\n\n"
                    f"{metrics_list}\n\n"
                    f"**Contextual Summary**: These metrics directly support the document's central themes of {', '.join(doc_profile.key_concepts[:3])}.\n"
                    f"Would you like me to synthesize these figures into a comparative financial/technical summary table?"
                )

        # 3. Methodology, Framework & Architecture Query
        is_method_query = any(
            w in user_query
            for w in ["method", "methodology", "architecture", "framework", "how does", "workflow", "process", "implementation", "approach"]
        )
        if is_method_query:
            method_sections = [
                s for s in doc_profile.section_map
                if any(k in s["title"].lower() for k in ["method", "approach", "architect", "design", "process", "system", "workflow", "model"])
            ]
            if method_sections:
                sec_bullets = "\n".join(f"#### {ms['title']}\n{ms['preview']}\n" for ms in method_sections[:4])
                return (
                    f"### Methodology & Architectural Blueprint: `{doc_profile.filename}`\n\n"
                    f"The document outlines its core approach across specific procedural and architectural sections:\n\n"
                    f"{sec_bullets}\n\n"
                    f"**Grounding Note**: The operational steps correlate with the document's primary objectives around {', '.join(doc_profile.key_concepts[:2])}.\n"
                    f"Would you like me to diagram the step-by-step workflow or analyze potential implementation bottlenecks?"
                )

        # 4. Critical Search & Deep Sentence Relevance Matching
        words = [w for w in re.findall(r"\b[a-zA-Z]{3,}\b", user_query) if w not in _STOPWORDS]
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", full_text) if len(s.strip()) > 20]

        scored_sents = []
        for s in sentences:
            score = sum(1 for w in words if w in s.lower())
            if score > 0:
                scored_sents.append((score, s))

        scored_sents.sort(key=lambda x: x[0], reverse=True)
        top_matches = [s for _, s in scored_sents[:6]]

        if top_matches:
            evidence_points = "\n\n".join(f"- **Finding**: {s}" for s in top_matches)
            
            # Find closest section
            matched_sections = []
            for sec in doc_profile.section_map:
                if any(w in sec["title"].lower() or w in sec["preview"].lower() for w in words):
                    matched_sections.append(sec["title"])

            section_cite = f" (specifically relevant to sections: {', '.join(f'`{sec}`' for sec in matched_sections[:3])})" if matched_sections else ""

            return (
                f"### Analysis & Detailed Explanation: *\"{raw_query}\"*\n\n"
                f"Based on a rigorous whole-document evaluation of **{doc_profile.filename}**{section_cite}, here are the core findings and context:\n\n"
                f"{evidence_points}\n\n"
                f"#### Synthesis & Context\n"
                f"The points above directly inform the document's broader narrative on **{', '.join(doc_profile.key_concepts[:3])}**. "
                f"In the context of the whole document, this indicates a cohesive alignment with the central thesis:\n\n"
                f"> *\"{doc_profile.executive_summary[:280]}...\"*\n\n"
                f"Would you like further clarification on this topic or an explanation of related sections?"
            )

        # 5. Topic not explicitly found in document
        return (
            f"### Document Grounding Analysis: `{doc_profile.filename}`\n\n"
            f"I analyzed the complete document (**{doc_profile.word_count:,} words** across **{len(doc_profile.section_map)} sections**). "
            f"The specific query *\"{raw_query}\"* does not have a direct textual mention in the text.\n\n"
            f"#### What the document DOES cover:\n"
            f"The document primarily explores:\n"
            f"{', '.join(f'`{c}`' for c in doc_profile.key_concepts)}\n\n"
            f"**Executive Takeaway**:\n"
            f"> {doc_profile.executive_summary}\n\n"
            f"Try asking about one of the core themes above or inspect the document outline for specific sections!"
        )
