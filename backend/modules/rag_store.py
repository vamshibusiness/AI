from pathlib import Path
import pickle

import faiss
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DOCS_DIR = PROJECT_ROOT / "docs"

INDEX_DIR = PROJECT_ROOT / "backend" / "assets" / "rag"
INDEX_PATH = INDEX_DIR / "jarvis_docs.faiss"
META_PATH = INDEX_DIR / "jarvis_docs.pkl"

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None
_index = None
_metadata = None


def get_embedding_model():
    global _model

    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    return _model


def save_index(index, metadata):
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    faiss.write_index(index, str(INDEX_PATH))

    with open(META_PATH, "wb") as f:
        pickle.dump(metadata, f)


def load_index():
    if not INDEX_PATH.exists() or not META_PATH.exists():
        return None, []

    index = faiss.read_index(str(INDEX_PATH))

    with open(META_PATH, "rb") as f:
        metadata = pickle.load(f)

    return index, metadata



def load_index():
    global _index, _metadata

    if _index is not None and _metadata is not None:
        return _index, _metadata

    if not INDEX_PATH.exists() or not META_PATH.exists():
        return None, []

    _index = faiss.read_index(str(INDEX_PATH))

    with open(META_PATH, "rb") as f:
        _metadata = pickle.load(f)

    return _index, _metadata


def warm_rag():
    get_embedding_model()
    load_index()
    print("[RAG] Knowledge engine warmed.")