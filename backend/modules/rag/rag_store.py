# backend/modules/rag/rag_store.py
"""
Persistent Vector Store and Document Catalog for JARVIS RAG.

Uses:
- FAISS IndexFlatIP (cosine similarity over normalized embeddings)
- SentenceTransformers (all-MiniLM-L6-v2)
- SHA-256 hash tracking for incremental ingestion
"""

from pathlib import Path
import pickle
import json
import time
from typing import Tuple, List, Dict, Any, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from backend.modules.rag.pdf_loader import extract_file_chunks, compute_file_hash

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DOCS_DIR = PROJECT_ROOT / "docs"
INDEX_DIR = PROJECT_ROOT / "backend" / "assets" / "rag"
UPLOAD_DIR = INDEX_DIR / "uploaded"

INDEX_PATH = INDEX_DIR / "jarvis_docs.faiss"
META_PATH = INDEX_DIR / "jarvis_docs.pkl"
HASHES_PATH = INDEX_DIR / "doc_hashes.json"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None
_index = None
_metadata: List[Dict[str, Any]] = []

def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model

def load_document_hashes() -> Dict[str, str]:
    if not HASHES_PATH.exists():
        return {}
    try:
        with open(HASHES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_document_hashes(hashes: Dict[str, str]):
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    with open(HASHES_PATH, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2)

def save_index(index: faiss.Index, metadata: List[Dict[str, Any]]):
    global _index, _metadata
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    with open(META_PATH, "wb") as f:
        pickle.dump(metadata, f)
    _index = index
    _metadata = metadata

def load_index(force_reload: bool = False) -> Tuple[Optional[faiss.Index], List[Dict[str, Any]]]:
    global _index, _metadata
    if not force_reload and _index is not None and _metadata:
        return _index, _metadata

    if not INDEX_PATH.exists() or not META_PATH.exists():
        return None, []

    try:
        _index = faiss.read_index(str(INDEX_PATH))
        with open(META_PATH, "rb") as f:
            _metadata = pickle.load(f)
        return _index, _metadata
    except Exception as e:
        print(f"[RAG] Failed to load index: {e}")
        return None, []

def index_document(file_path: Path) -> Dict[str, Any]:
    """
    Incrementally indexes a single document (PDF, TXT, MD, CSV).
    Checks SHA-256 hash to skip if already indexed.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return {"ok": False, "error": f"File not found: {file_path}"}

    doc_hash = compute_file_hash(file_path)
    hashes = load_document_hashes()

    # Check if unchanged
    if hashes.get(file_path.name) == doc_hash:
        return {
            "ok": True,
            "status": "already_indexed",
            "filename": file_path.name,
            "hash": doc_hash,
            "message": "Document is already indexed and unchanged.",
        }

    # Extract chunks
    chunks = extract_file_chunks(file_path)
    if not chunks:
        return {"ok": False, "error": f"No valid text could be extracted from {file_path.name}"}

    model = get_embedding_model()
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

    curr_index, curr_metadata = load_index()

    if curr_index is None or not curr_metadata:
        dimension = embeddings.shape[1]
        new_index = faiss.IndexFlatIP(dimension)
        new_index.add(embeddings)
        new_metadata = list(chunks)
    else:
        existing_sources = {c.get("source") for c in curr_metadata}
        if file_path.name not in existing_sources:
            # Brand new file: simply add embeddings to current FAISS index
            curr_index.add(embeddings)
            curr_metadata.extend(chunks)
            new_index = curr_index
            new_metadata = curr_metadata
        else:
            # Updating modified existing file: rebuild index
            new_metadata = [c for c in curr_metadata if c.get("source") != file_path.name]
            new_metadata.extend(chunks)
            all_texts = [c["text"] for c in new_metadata]
            all_embeddings = model.encode(all_texts, convert_to_numpy=True, normalize_embeddings=True)
            dimension = all_embeddings.shape[1]
            new_index = faiss.IndexFlatIP(dimension)
            new_index.add(all_embeddings)

    save_index(new_index, new_metadata)
    hashes[file_path.name] = doc_hash
    save_document_hashes(hashes)

    return {
        "ok": True,
        "status": "indexed",
        "filename": file_path.name,
        "hash": doc_hash,
        "chunks_added": len(chunks),
        "total_chunks": len(new_metadata),
    }

def list_indexed_documents() -> List[Dict[str, Any]]:
    _, metadata = load_index()
    hashes = load_document_hashes()
    docs = {}

    for chunk in metadata:
        src = chunk.get("source", "unknown")
        page = chunk.get("page", 1)
        if src not in docs:
            docs[src] = {
                "filename": src,
                "hash": hashes.get(src, ""),
                "chunks_count": 0,
                "pages": set(),
            }
        docs[src]["chunks_count"] += 1
        docs[src]["pages"].add(page)

    result = []
    for src, info in docs.items():
        result.append({
            "filename": info["filename"],
            "hash": info["hash"],
            "chunks_count": info["chunks_count"],
            "chunk_count": info["chunks_count"],
            "page_count": len(info["pages"]),
            "pages": len(info["pages"]),
        })
    return result

def warm_rag():
    get_embedding_model()
    load_index()
    print("[RAG] Knowledge engine warmed.")