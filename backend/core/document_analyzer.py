"""
document_analyzer.py — Whole-Document Structural & Semantic NLP Analyzer.

Performs macro-level NLP analysis across the entire document:
  - TextRank sentence centrality (Executive Spine Summary)
  - TF-IDF key concept and domain terminology extraction
  - Structural section mapping
  - Quantitative metrics (reading time, word count, complexity)
"""

from __future__ import annotations

import collections
import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from core.document_parser import DocumentSection, ParsedDocument

_STOPWORDS = frozenset(
    {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
        "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
        "below", "between", "both", "but", "by", "can", "cannot", "could", "did", "do",
        "does", "doing", "don't", "down", "during", "each", "few", "for", "from",
        "further", "had", "has", "have", "having", "he", "her", "here", "hers",
        "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is",
        "isn't", "it", "it's", "its", "itself", "just", "me", "more", "most", "my",
        "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
        "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so",
        "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
        "then", "there", "these", "they", "this", "those", "through", "to", "too",
        "under", "until", "up", "very", "was", "we", "were", "what", "when", "where",
        "which", "while", "who", "whom", "why", "with", "would", "you", "your",
        "yours", "yourself", "yourselves", "will", "shall", "may", "might", "must",
    }
)


@dataclass
class DocumentProfile:
    filename: str
    file_type: str
    word_count: int
    char_count: int
    estimated_read_time_mins: int
    key_concepts: list[str]
    executive_summary: str
    section_map: list[dict[str, Any]]
    full_text_preview: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentProfile:
        return cls(**data)


def _clean_tokens(text: str) -> list[str]:
    """Tokenize and filter to lowercased alphanumeric words."""
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    return [w for w in words if w not in _STOPWORDS]


def _extract_key_concepts(text: str, top_n: int = 12) -> list[str]:
    """Extract top domain terms using TF-IDF-inspired term frequency ranking."""
    tokens = _clean_tokens(text)
    if not tokens:
        return []

    # Unigram counts
    freq = collections.Counter(tokens)

    # Bigram counts (e.g. "machine learning", "space telescope")
    words_raw = re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())
    bigrams: list[str] = []
    for i in range(len(words_raw) - 1):
        w1, w2 = words_raw[i], words_raw[i + 1]
        if w1 not in _STOPWORDS and w2 not in _STOPWORDS:
            bigrams.append(f"{w1} {w2}")
    bigram_freq = collections.Counter(bigrams)

    # Merge top bigrams (weight x2) and unigrams
    scored: dict[str, float] = {}
    for term, count in freq.most_common(30):
        scored[term] = count * 1.0
    for term, count in bigram_freq.most_common(15):
        if count >= 2:
            scored[term] = count * 2.2

    # Sort descending
    sorted_terms = sorted(scored.items(), key=lambda x: x[1], reverse=True)
    return [t[0].title() for t in sorted_terms[:top_n]]


def _split_into_sentences(text: str) -> list[str]:
    """Sentence tokenizer with minimum length filter."""
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z\d\"])", text)
    sentences = [s.strip().replace("\n", " ") for s in raw if len(s.strip()) > 25]
    return sentences


def _textrank_executive_summary(text: str, num_sentences: int = 5) -> str:
    """
    Extracts the most central/authoritative sentences across the whole document
    using an algorithm modeled on TextRank / LexRank graph centrality.
    """
    sentences = _split_into_sentences(text)
    if not sentences:
        return text[:500]
    if len(sentences) <= num_sentences:
        return " ".join(sentences)

    # Pre-tokenize sentences for similarity graph
    sent_tokens = [_clean_tokens(s) for s in sentences]
    n = len(sentences)

    # Build similarity matrix based on token overlap (Jaccard similarity)
    scores = [0.0] * n
    for i in range(n):
        set_i = set(sent_tokens[i])
        if not set_i:
            continue
        for j in range(i + 1, n):
            set_j = set(sent_tokens[j])
            if not set_j:
                continue
            intersection = len(set_i & set_j)
            if intersection > 0:
                sim = intersection / (math.log(len(set_i) + 1) + math.log(len(set_j) + 1))
                scores[i] += sim
                scores[j] += sim

    # Rank sentences by centrality score
    ranked_indices = sorted(range(n), key=lambda idx: scores[idx], reverse=True)[:num_sentences]
    # Re-order by original chronological appearance in document
    ranked_indices.sort()

    summary_sentences = [sentences[idx] for idx in ranked_indices]
    return " ".join(summary_sentences)


class WholeDocumentAnalyzer:
    """
    Analyzes an ingested document globally. Produces an executive profile
    and contextual payload ready for multi-turn LLM conversation.
    """

    def analyze(self, parsed: ParsedDocument) -> DocumentProfile:
        word_count = parsed.word_count
        read_time_mins = max(1, round(word_count / 200))

        key_concepts = _extract_key_concepts(parsed.raw_text, top_n=10)
        executive_summary = _textrank_executive_summary(parsed.raw_text, num_sentences=4)

        # Build section map
        section_map: list[dict[str, Any]] = []
        for s in parsed.sections:
            section_map.append(
                {
                    "title": s.title,
                    "preview": s.content[:150] + "..." if len(s.content) > 150 else s.content,
                    "word_count": len(s.content.split()),
                    "index": s.page_or_index,
                }
            )

        return DocumentProfile(
            filename=parsed.filename,
            file_type=parsed.file_type,
            word_count=word_count,
            char_count=parsed.char_count,
            estimated_read_time_mins=read_time_mins,
            key_concepts=key_concepts,
            executive_summary=executive_summary,
            section_map=section_map,
            full_text_preview=parsed.raw_text[:1200],
            metadata=parsed.metadata,
        )
