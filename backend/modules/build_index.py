from pathlib import Path
import re

import faiss

from backend.modules.rag.rag_store import (
    DOCS_DIR,
    get_embedding_model,
    save_index,
)


def split_markdown_into_chunks(file_path: Path) -> list[dict]:
    text = file_path.read_text(encoding="utf-8")

    # Split on markdown headings while keeping heading text.
    sections = re.split(r"(?=^#{1,3}\s+)", text, flags=re.MULTILINE)

    chunks = []

    for section in sections:
        section = section.strip()

        if not section:
            continue

        lines = section.splitlines()
        heading = lines[0].replace("#", "").strip() if lines else file_path.stem

        chunks.append({
            "source": file_path.name,
            "heading": heading,
            "text": section,
        })

    return chunks


def build_index():
    if not DOCS_DIR.exists():
        raise FileNotFoundError(f"Docs folder not found: {DOCS_DIR}")

    all_chunks = []

    for file_path in sorted(DOCS_DIR.glob("*.md")):
        chunks = split_markdown_into_chunks(file_path)
        all_chunks.extend(chunks)

    if not all_chunks:
        raise ValueError("No markdown chunks found in docs folder.")

    texts = [chunk["text"] for chunk in all_chunks]

    model = get_embedding_model()

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    save_index(index, all_chunks)

    print(f"RAG index built successfully.")
    print(f"Documents folder: {DOCS_DIR}")
    print(f"Chunks indexed: {len(all_chunks)}")


if __name__ == "__main__":
    build_index()