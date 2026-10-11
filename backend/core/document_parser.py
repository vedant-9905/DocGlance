"""
document_parser.py — Universal Document Ingestion for DocGlance.

Supports:
  - PDF documents (.pdf)
  - Microsoft Word & Google Docs (.docx, .doc)
  - Microsoft Excel & Google Sheets (.xlsx, .xls, .csv, .tsv)
  - Microsoft PowerPoint & Google Slides (.pptx)
  - Web & Rich Text (.html, .htm)
  - Plain Text & Markdown (.txt, .md, .rst, .json, .yaml)
"""

from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import bs4
import docx
import openpyxl
import pandas as pd
import pptx
import pypdf

logger = logging.getLogger(__name__)


@dataclass
class DocumentSection:
    title: str
    content: str
    page_or_index: int = 1


@dataclass
class ParsedDocument:
    filename: str
    file_type: str
    raw_text: str
    word_count: int
    char_count: int
    sections: list[DocumentSection] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _parse_pdf(file_bytes: bytes, filename: str) -> ParsedDocument:
    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
    sections: list[DocumentSection] = []
    full_text_parts: list[str] = []

    for idx, page in enumerate(reader.pages):
        page_text = (page.extract_text() or "").strip()
        if page_text:
            sections.append(
                DocumentSection(
                    title=f"Page {idx + 1}",
                    content=page_text,
                    page_or_index=idx + 1,
                )
            )
            full_text_parts.append(f"--- Page {idx + 1} ---\n{page_text}")

    full_text = "\n\n".join(full_text_parts)

    # Secondary fallback with PyMuPDF for complex or malformed PDFs
    if not full_text.strip():
        try:
            import pymupdf
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            for idx, page in enumerate(doc):
                page_text = (page.get_text() or "").strip()
                if page_text:
                    sections.append(
                        DocumentSection(
                            title=f"Page {idx + 1}",
                            content=page_text,
                            page_or_index=idx + 1,
                        )
                    )
                    full_text_parts.append(f"--- Page {idx + 1} ---\n{page_text}")
            full_text = "\n\n".join(full_text_parts)
        except Exception as exc:
            logger.warning("PyMuPDF fallback failed for %s: %s", filename, exc)

    return ParsedDocument(
        filename=filename,
        file_type="PDF",
        raw_text=full_text,
        word_count=len(full_text.split()),
        char_count=len(full_text),
        sections=sections,
        metadata={"total_pages": len(reader.pages)},
    )


def _parse_docx(file_bytes: bytes, filename: str) -> ParsedDocument:
    doc = docx.Document(io.BytesIO(file_bytes))
    sections: list[DocumentSection] = []
    full_text_parts: list[str] = []

    current_title = "Introduction / Overview"
    current_content: list[str] = []
    section_idx = 1

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # Check if heading
        if para.style and para.style.name and para.style.name.startswith("Heading"):
            if current_content:
                sections.append(
                    DocumentSection(
                        title=current_title,
                        content="\n".join(current_content),
                        page_or_index=section_idx,
                    )
                )
                section_idx += 1
                current_content = []
            current_title = text
            full_text_parts.append(f"## {text}")
        else:
            current_content.append(text)
            full_text_parts.append(text)

    # Tables
    for t_idx, table in enumerate(doc.tables):
        table_rows: list[str] = []
        for row in table.rows:
            row_data = [cell.text.strip() for cell in row.cells]
            table_rows.append(" | ".join(row_data))
        if table_rows:
            table_md = "\n".join(table_rows)
            full_text_parts.append(f"\n[Table {t_idx + 1}]:\n{table_md}\n")
            current_content.append(f"[Table {t_idx + 1}]:\n{table_md}")

    if current_content:
        sections.append(
            DocumentSection(
                title=current_title,
                content="\n".join(current_content),
                page_or_index=section_idx,
            )
        )

    full_text = "\n\n".join(full_text_parts)
    return ParsedDocument(
        filename=filename,
        file_type="Word (DOCX)",
        raw_text=full_text,
        word_count=len(full_text.split()),
        char_count=len(full_text),
        sections=sections,
        metadata={"total_sections": len(sections), "total_tables": len(doc.tables)},
    )


def _parse_excel(file_bytes: bytes, filename: str) -> ParsedDocument:
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    sections: list[DocumentSection] = []
    full_text_parts: list[str] = []

    for s_idx, sheet_name in enumerate(wb.sheetnames):
        ws = wb[sheet_name]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue

        sheet_text_lines: list[str] = []
        header = [str(c or "") for c in rows[0]]
        sheet_text_lines.append(f"Sheet: {sheet_name}")
        sheet_text_lines.append("Columns: " + ", ".join(header))

        # Sample rows up to 50 rows for full text
        sample_rows = rows[1:51]
        for r in sample_rows:
            row_vals = [str(c) if c is not None else "" for c in r]
            if any(row_vals):
                sheet_text_lines.append(" | ".join(row_vals))

        content = "\n".join(sheet_text_lines)
        sections.append(
            DocumentSection(
                title=f"Sheet: {sheet_name}",
                content=content,
                page_or_index=s_idx + 1,
            )
        )
        full_text_parts.append(f"=== Sheet: {sheet_name} ({len(rows)} rows) ===\n{content}")

    full_text = "\n\n".join(full_text_parts)
    return ParsedDocument(
        filename=filename,
        file_type="Excel Spreadsheet",
        raw_text=full_text,
        word_count=len(full_text.split()),
        char_count=len(full_text),
        sections=sections,
        metadata={"sheets": wb.sheetnames, "total_sheets": len(wb.sheetnames)},
    )


def _parse_csv(file_bytes: bytes, filename: str) -> ParsedDocument:
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception:
        df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin1")

    shape_info = f"Dataset Dimensions: {df.shape[0]} rows, {df.shape[1]} columns"
    cols = list(df.columns)
    summary_lines = [shape_info, f"Columns: {', '.join(cols)}", "\nSample Records (First 20 rows):"]

    for idx, row in df.head(20).iterrows():
        summary_lines.append(f"Row {idx + 1}: " + ", ".join(f"{col}={val}" for col, val in row.items()))

    # Statistical summary if numeric columns exist
    num_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if num_cols:
        summary_lines.append("\nNumeric Column Summaries (Min, Max, Mean):")
        for col in num_cols[:10]:
            summary_lines.append(
                f"- {col}: min={df[col].min()}, max={df[col].max()}, mean={round(df[col].mean(), 2)}"
            )

    full_text = "\n".join(summary_lines)
    return ParsedDocument(
        filename=filename,
        file_type="CSV / Tabular Data",
        raw_text=full_text,
        word_count=len(full_text.split()),
        char_count=len(full_text),
        sections=[DocumentSection(title="Tabular Overview & Schema", content=full_text, page_or_index=1)],
        metadata={"rows": df.shape[0], "columns": df.shape[1], "column_names": cols},
    )


def _parse_pptx(file_bytes: bytes, filename: str) -> ParsedDocument:
    prs = pptx.Presentation(io.BytesIO(file_bytes))
    sections: list[DocumentSection] = []
    full_text_parts: list[str] = []

    for idx, slide in enumerate(prs.slides):
        slide_lines: list[str] = []
        slide_title = f"Slide {idx + 1}"

        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    t = para.text.strip()
                    if t:
                        if not slide_lines:
                            slide_title = f"Slide {idx + 1}: {t[:40]}"
                        slide_lines.append(t)

        content = "\n".join(slide_lines)
        if content:
            sections.append(
                DocumentSection(
                    title=slide_title,
                    content=content,
                    page_or_index=idx + 1,
                )
            )
            full_text_parts.append(f"--- {slide_title} ---\n{content}")

    full_text = "\n\n".join(full_text_parts)
    return ParsedDocument(
        filename=filename,
        file_type="PowerPoint Presentation",
        raw_text=full_text,
        word_count=len(full_text.split()),
        char_count=len(full_text),
        sections=sections,
        metadata={"total_slides": len(prs.slides)},
    )


def _parse_html(file_bytes: bytes, filename: str) -> ParsedDocument:
    html_text = file_bytes.decode("utf-8", errors="replace")
    soup = bs4.BeautifulSoup(html_text, "html.parser")
    # Remove script and style tags
    for s in soup(["script", "style", "nav", "footer"]):
        s.extract()

    text = soup.get_text(separator="\n")
    clean_lines = [line.strip() for line in text.splitlines() if line.strip()]
    full_text = "\n".join(clean_lines)

    return ParsedDocument(
        filename=filename,
        file_type="HTML / Rich Text",
        raw_text=full_text,
        word_count=len(full_text.split()),
        char_count=len(full_text),
        sections=[DocumentSection(title="Document Body", content=full_text[:3000], page_or_index=1)],
        metadata={"title": soup.title.string if soup.title else filename},
    )


def _parse_plain_text(file_bytes: bytes, filename: str) -> ParsedDocument:
    full_text = file_bytes.decode("utf-8", errors="replace")
    # Build pseudo sections based on blank lines or markdown headers
    sections: list[DocumentSection] = []
    lines = full_text.splitlines()
    curr_sec: list[str] = []
    curr_title = "Beginning of Document"
    sec_num = 1

    for line in lines:
        if line.startswith("# ") or line.startswith("## "):
            if curr_sec:
                sections.append(DocumentSection(title=curr_title, content="\n".join(curr_sec), page_or_index=sec_num))
                sec_num += 1
                curr_sec = []
            curr_title = line.lstrip("#").strip()
        else:
            curr_sec.append(line)

    if curr_sec:
        sections.append(DocumentSection(title=curr_title, content="\n".join(curr_sec), page_or_index=sec_num))

    ext = Path(filename).suffix.lower()
    type_name = "Markdown" if ext in {".md", ".markdown"} else "Plain Text"

    return ParsedDocument(
        filename=filename,
        file_type=type_name,
        raw_text=full_text,
        word_count=len(full_text.split()),
        char_count=len(full_text),
        sections=sections or [DocumentSection(title="Content", content=full_text, page_or_index=1)],
        metadata={"lines": len(lines)},
    )


def parse_any_document(file_bytes: bytes, filename: str) -> ParsedDocument:
    """Universal parser dispatch based on file extension."""
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return _parse_pdf(file_bytes, filename)
    elif ext in {".docx", ".doc"}:
        return _parse_docx(file_bytes, filename)
    elif ext in {".xlsx", ".xls"}:
        return _parse_excel(file_bytes, filename)
    elif ext in {".csv", ".tsv"}:
        return _parse_csv(file_bytes, filename)
    elif ext in {".pptx", ".ppt"}:
        return _parse_pptx(file_bytes, filename)
    elif ext in {".html", ".htm"}:
        return _parse_html(file_bytes, filename)
    elif ext in {".txt", ".md", ".markdown", ".rst", ".json", ".yaml", ".yml", ".xml"}:
        return _parse_plain_text(file_bytes, filename)
    else:
        # Fallback to plain text decode
        return _parse_plain_text(file_bytes, filename)
