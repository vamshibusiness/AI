# backend/modules/rag/build_index.py
"""
Builds or updates the RAG FAISS index for all documents in docs/ and uploaded/.
"""

from pathlib import Path
from backend.modules.rag.rag_store import (
    DOCS_DIR,
    UPLOAD_DIR,
    index_document,
    load_index,
    list_indexed_documents,
)

def build_index():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    search_dirs = [DOCS_DIR, UPLOAD_DIR]
    supported_extensions = [".pdf", ".md", ".txt", ".csv"]

    indexed_count = 0
    skipped_count = 0

    for directory in search_dirs:
        for ext in supported_extensions:
            for file_path in sorted(directory.glob(f"*{ext}")):
                res = index_document(file_path)
                if res.get("status") == "indexed":
                    indexed_count += 1
                    print(f"[RAG] Indexed: {file_path.name} ({res.get('chunks_added')} chunks)")
                elif res.get("status") == "already_indexed":
                    skipped_count += 1
                    print(f"[RAG] Up to date: {file_path.name}")
                else:
                    print(f"[RAG] Error on {file_path.name}: {res.get('error')}")

    docs = list_indexed_documents()
    print(f"\n[RAG Summary] Indexed {indexed_count} new/modified, {skipped_count} skipped. Total indexed documents: {len(docs)}")
    return docs

if __name__ == "__main__":
    build_index()