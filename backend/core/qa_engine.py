"""
qa_engine.py — Generative QA pipeline (google/flan-t5-base).

Optimisations vs v1:
  - Settings imported from config.py
  - Tokenizer truncation applied before passing to pipeline (avoids
    silent truncation / silent OOM inside the model)
  - Prompt context capped per-chunk to avoid blowing the input window
  - Thread-safe double-checked singleton load
"""

from __future__ import annotations

import logging
import textwrap
import threading
from typing import Any

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

from config import (
    QA_MAX_INPUT_TOKENS,
    QA_MAX_NEW_TOKENS,
    QA_MODEL_NAME,
    QA_REPETITION_PENALTY,
    QA_TEMPERATURE,
    QA_TOP_P,
)

logger = logging.getLogger(__name__)

_qa_pipeline: Any = None
_lock = threading.Lock()

# Per-chunk text budget so many small chunks don't overflow the model window
_CHARS_PER_CHUNK = 600


def _get_qa_pipeline() -> Any:
    global _qa_pipeline
    if _qa_pipeline is None:
        with _lock:
            if _qa_pipeline is None:
                logger.info("Loading QA model: %s", QA_MODEL_NAME)
                tokenizer = AutoTokenizer.from_pretrained(QA_MODEL_NAME)
                model = AutoModelForSeq2SeqLM.from_pretrained(QA_MODEL_NAME)
                _qa_pipeline = pipeline(
                    "text2text-generation",
                    model=model,
                    tokenizer=tokenizer,
                    max_new_tokens=QA_MAX_NEW_TOKENS,
                    temperature=QA_TEMPERATURE,
                    top_p=QA_TOP_P,
                    repetition_penalty=QA_REPETITION_PENALTY,
                    do_sample=True,
                )
                logger.info("QA pipeline ready")
    return _qa_pipeline


def _build_prompt(query: str, contexts: list[dict[str, Any]]) -> str:
    context_block = ""
    for i, ctx in enumerate(contexts):
        snippet = ctx["text"][:_CHARS_PER_CHUNK]
        source = ctx.get("source", "unknown")
        cid = ctx.get("chunk_id", f"chunk_{i}")
        context_block += (
            f"[SOURCE {i + 1} | id={cid} | file={source}]\n{snippet}\n\n"
        )

    return textwrap.dedent(f"""
        You are DocGlance, a precise question-answering assistant.
        Answer the question using ONLY the information from the context below.
        If the context lacks sufficient information, respond:
        "The provided documents do not contain sufficient information to answer this question."
        Do NOT use prior knowledge. Cite source IDs inline when referencing facts.

        CONTEXT:
        {context_block.strip()}

        QUESTION: {query}

        ANSWER:
    """).strip()


class QAEngine:
    """
    Singleton-backed seq2seq QA engine.
    Call ``answer(query, contexts)`` to generate a grounded response.
    """

    def __init__(self) -> None:
        _get_qa_pipeline()  # eager load

    def answer(
        self,
        query: str,
        contexts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Generate a grounded answer.

        Returns
        -------
        dict:
            ``answer``        — generated text string
            ``prompt_tokens`` — token count of the truncated prompt
        """
        if not contexts:
            return {
                "answer": "No relevant documents were found to answer this question.",
                "prompt_tokens": 0,
            }

        pipe = _get_qa_pipeline()
        prompt = _build_prompt(query, contexts)

        # Hard-truncate to model's max input length before inference
        tokenizer: AutoTokenizer = pipe.tokenizer  # type: ignore[attr-defined]
        encoded = tokenizer(
            prompt,
            truncation=True,
            max_length=QA_MAX_INPUT_TOKENS,
            return_tensors="pt",
        )
        prompt_tokens: int = encoded["input_ids"].shape[-1]

        # Decode the (possibly truncated) prompt back to text for the pipeline
        truncated_prompt: str = tokenizer.decode(
            encoded["input_ids"][0], skip_special_tokens=True
        )

        outputs = pipe(truncated_prompt)
        answer_text: str = outputs[0]["generated_text"].strip()  # type: ignore[index]

        # Strip echoed prompt prefix if model copies it
        if "ANSWER:" in answer_text:
            answer_text = answer_text.split("ANSWER:")[-1].strip()

        return {"answer": answer_text, "prompt_tokens": prompt_tokens}
