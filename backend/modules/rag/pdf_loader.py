# backend/modules/rag/pdf_loader.py
"""
Multi-format Document Loader and Chunker for JARVIS RAG.

Supports:
- PDF (page-aware text extraction via pypdf)
- Markdown (.md)
- Plain text (.txt)
- CSV files (.csv)

Features:
- SHA-256 hash tracking to prevent re-indexing unchanged documents
- Overlapping semantic chunking preserving page numbers and headings
- Clean character normalization
"""

import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

def compute_file_hash(file_path: Path) -> str:
    """Computes SHA-256 checksum of a file for incremental indexing."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def clean_text(text: str) -> str:
    if not text:
        return ""
    # Normalize line breaks and repeated spaces
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def chunk_text(
    text: str,
    source_name: str,
    doc_hash: str,
    page_number: Optional[int] = None,
    section_heading: Optional[str] = None,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> List[Dict[str, Any]]:
    """Splits text into overlapping chunks, tracking document, page, and chunk id."""
    text = clean_text(text)
    if not text:
        return []

    chunks = []
    start = 0
    chunk_idx = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)

        # Try to break on a sentence or newline boundary if possible
        if end < text_len:
            split_pos = max(
                text.rfind(". ", start, end),
                text.rfind("\n", start, end),
                text.rfind("; ", start, end),
            )
            if split_pos > start + int(chunk_size * 0.5):
                end = split_pos + 1

        chunk_content = text[start:end].strip()
        if chunk_content:
            chunks.append({
                "chunk_id": f"{source_name}_p{page_number or 1}_c{chunk_idx}",
                "source": source_name,
                "doc_hash": doc_hash,
                "page": page_number or 1,
                "heading": section_heading or source_name,
                "text": chunk_content,
            })
            chunk_idx += 1

        if end >= text_len:
            break
        start = end - chunk_overlap

    return chunks

def extract_pdf_chunks(file_path: Path, doc_hash: str) -> List[Dict[str, Any]]:
    if PdfReader is None:
        raise RuntimeError("pypdf is required to process PDF files.")

    reader = PdfReader(str(file_path))
    chunks = []

    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        page_text = page.extract_text() or ""
        page_chunks = chunk_text(
            text=page_text,
            source_name=file_path.name,
            doc_hash=doc_hash,
            page_number=page_num,
            section_heading=f"Page {page_num}",
        )
        chunks.extend(page_chunks)

    return chunks

def extract_markdown_chunks(file_path: Path, doc_hash: str) -> List[Dict[str, Any]]:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    sections = re.split(r"(?=^#{1,3}\s+)", text, flags=re.MULTILINE)
    chunks = []

    for section in sections:
        section = section.strip()
        if not section:
            continue
        lines = section.splitlines()
        heading = lines[0].replace("#", "").strip() if lines else file_path.stem
        sub_chunks = chunk_text(
            text=section,
            source_name=file_path.name,
            doc_hash=doc_hash,
            section_heading=heading,
        )
        chunks.extend(sub_chunks)

    return chunks

def extract_text_chunks(file_path: Path, doc_hash: str) -> List[Dict[str, Any]]:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    return chunk_text(
        text=text,
        source_name=file_path.name,
        doc_hash=doc_hash,
        section_heading=file_path.stem,
    )

def extract_file_chunks(file_path: Path) -> List[Dict[str, Any]]:
    """Loads and chunks any supported document type with SHA-256 calculation."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    doc_hash = compute_file_hash(file_path)
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        return extract_pdf_chunks(file_path, doc_hash)
    elif ext in [".md", ".markdown"]:
        return extract_markdown_chunks(file_path, doc_hash)
    elif ext in [".txt", ".csv", ".json", ".log"]:
        return extract_text_chunks(file_path, doc_hash)
    else:
        # Fallback raw read
        return extract_text_chunks(file_path, doc_hash)
