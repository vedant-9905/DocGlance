"""
verifier.py — NLI-based hallucination verifier.

Optimisations vs v1:
  - Settings imported from config.py
  - Thread-safe double-checked singleton load
  - apply_softmax=True (native) removes the manual scipy softmax call
    and reduces an import dependency
  - Batch NLI predictions over all (chunk, claim) pairs in one call
    instead of per-claim loops — significant speedup for many chunks
  - Claims that are too short (< 12 chars) are filtered before scoring
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from typing import Any

import numpy as np
from sentence_transformers import CrossEncoder

from config import (
    NLI_CONTRADICTION_THRESHOLD,
    NLI_ENTAILMENT_THRESHOLD,
    NLI_MODEL_NAME,
)

logger = logging.getLogger(__name__)

# cross-encoder/nli-deberta-v3-small label order: [contradiction, entailment, neutral]
_IDX_CONTRADICTION = 0
_IDX_ENTAILMENT = 1

_nli_model: CrossEncoder | None = None
_lock = threading.Lock()


def _get_nli_model() -> CrossEncoder:
    global _nli_model
    if _nli_model is None:
        with _lock:
            if _nli_model is None:
                logger.info("Loading NLI model: %s", NLI_MODEL_NAME)
                _nli_model = CrossEncoder(NLI_MODEL_NAME)
                logger.info("NLI model ready")
    return _nli_model


# ── Sentence splitter ────────────────────────────────────────────────────────

_SENT_BOUNDARY = re.compile(
    r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+(?=[A-Z\d\"])"
)
_MIN_CLAIM_LEN = 4


def _split_into_claims(text: str) -> list[str]:
    """
    Split *text* into individual claim sentences.
    Filters out empty fragments while ensuring concise factual answers are verified.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    raw = _SENT_BOUNDARY.split(text)

    sentences: list[str] = []
    for sent in raw:
        for sub in sent.split("\n"):
            sub = sub.strip()
            if len(sub) >= _MIN_CLAIM_LEN:
                sentences.append(sub)

    if not sentences and len(text) >= _MIN_CLAIM_LEN:
        sentences.append(text)

    return sentences


# ── HallucinationVerifier ────────────────────────────────────────────────────

class HallucinationVerifier:
    """
    NLI-based claim verifier using a cross-encoder.

    For each sentence in the answer, scores it against every retrieved
    chunk and assigns: VERIFIED | UNSUPPORTED | CONTRADICTORY.
    """

    def __init__(self) -> None:
        _get_nli_model()

    def verify(
        self,
        answer: str,
        contexts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Verify each claim in *answer* against *contexts*.

        Returns list of dicts:
            claim, status, confidence, matched_source_id
        """
        if not answer or not contexts:
            return []

        claims = _split_into_claims(answer)
        if not claims:
            return []

        model = _get_nli_model()

        # Build all (premise, hypothesis) pairs in one flat list for batch predict
        all_pairs: list[tuple[str, str]] = []
        for claim in claims:
            for ctx in contexts:
                all_pairs.append((ctx["text"], claim))

        n_ctx = len(contexts)
        # apply_softmax=True → model returns probabilities directly
        raw_scores: np.ndarray = np.array(
            model.predict(all_pairs, apply_softmax=True)
        )  # shape: (n_claims * n_ctx, 3)

        results: list[dict[str, Any]] = []
        for i, claim in enumerate(claims):
            # Slice the rows belonging to this claim
            slice_scores = raw_scores[i * n_ctx : (i + 1) * n_ctx]  # (n_ctx, 3)

            entail_scores = slice_scores[:, _IDX_ENTAILMENT]
            contra_scores = slice_scores[:, _IDX_CONTRADICTION]

            best_e_idx = int(entail_scores.argmax())
            best_e_score = float(entail_scores[best_e_idx])

            best_c_idx = int(contra_scores.argmax())
            best_c_score = float(contra_scores[best_c_idx])

            if best_e_score >= NLI_ENTAILMENT_THRESHOLD:
                status = "VERIFIED"
                confidence = round(best_e_score, 4)
                matched_source_id: str | None = contexts[best_e_idx]["chunk_id"]
            elif best_c_score >= NLI_CONTRADICTION_THRESHOLD:
                status = "CONTRADICTORY"
                confidence = round(best_c_score, 4)
                matched_source_id = contexts[best_c_idx]["chunk_id"]
            else:
                status = "UNSUPPORTED"
                confidence = round(float(slice_scores.max()), 4)
                matched_source_id = None

            results.append(
                {
                    "claim": claim,
                    "status": status,
                    "confidence": confidence,
                    "matched_source_id": matched_source_id,
                }
            )

        return results
