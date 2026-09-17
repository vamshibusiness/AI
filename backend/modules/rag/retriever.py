from backend.modules.rag.rag_store import get_embedding_model, load_index


def retrieve_docs(question: str, top_k: int = 3, min_score: float = 0.35) -> list[dict]:
    """
    Search the local FAISS index and return the most relevant documentation chunks.
    """

    index, metadata = load_index()

    if index is None or not metadata:
        return []

    model = get_embedding_model()

    question_embedding = model.encode(
        [question],
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    scores, indexes = index.search(question_embedding, top_k)

    results = []

    for score, idx in zip(scores[0], indexes[0]):
        if idx < 0:
            continue

        if float(score) < min_score:
            continue

        chunk = metadata[idx]

        results.append({
            "score": float(score),
            "source": chunk.get("source", "unknown"),
            "page": chunk.get("page", 1),
            "heading": chunk.get("heading", ""),
            "text": chunk.get("text", ""),
        })

    return results


