# RAG Knowledge Engine

## Purpose

The RAG Knowledge Engine allows Jarvis to answer questions about its own system using local Markdown documentation.

RAG stands for Retrieval Augmented Generation. In Jarvis, this means documentation is searched first, the most relevant sections are retrieved, and those sections are passed to the local LLM so Jarvis can answer from its own docs.

---

## User Experience

Typical flow:

1. User asks a question about Jarvis.
2. The Intent Router reaches the RAG handler.
3. RAG searches the local documentation index.
4. Relevant documentation chunks are retrieved.
5. The chunks are passed to Ollama.
6. Jarvis answers using the documentation.

Example commands:

- How does your wake word work?
- How do you send email?
- How does your research agent work?
- What is Beast Mode?
- What can Jarvis do?
- How does your memory system work?

---

## Features

### Local Documentation Search

Jarvis searches local Markdown files stored in:

 
docs/
```

These files act as the source of truth for Jarvis self-knowledge.

---

### Markdown Chunking

Documentation is split into searchable chunks.

Each chunk stores:

- Source file
- Heading
- Text content

These chunks are embedded and saved into a FAISS vector index.

---

### Local Embeddings

Jarvis uses a local Sentence Transformers embedding model:

 
sentence-transformers/all-MiniLM-L6-v2
```

This converts documentation chunks and user questions into vectors for semantic search.

---

### FAISS Vector Search

Jarvis uses FAISS to perform fast local similarity search.

The FAISS index stores vector embeddings for every documentation chunk.

---

### Ollama Answer Generation

After retrieving relevant chunks, Jarvis sends the documentation context to Ollama.

Ollama generates a natural, voice-friendly answer using the retrieved documentation.

---

### RAG-Based Intent Detection

The RAG handler can decide whether a user question is about Jarvis by checking retrieval confidence.

If the top documentation chunks score above the configured threshold, the request is routed to the RAG Knowledge Handler.

---

# Architecture

 
Markdown Docs
↓
Chunking
↓
Embedding Model
↓
FAISS Index
↓
Retriever
↓
Knowledge Service
↓
Ollama
↓
Voice Response
```

---

# Module Breakdown

## build_index.py

### Purpose

Builds the local RAG index from Markdown documentation.

### Responsibilities

- Read Markdown files from `docs/`
- Split files into chunks
- Generate embeddings
- Build FAISS index
- Save index and metadata

Run this when documentation changes:

```bash
python -m backend.modules.rag.build_index
```

---

## rag_store.py

### Purpose

Stores shared RAG paths and loading logic.

### Responsibilities

- Define docs path
- Define FAISS index path
- Define metadata path
- Load embedding model
- Save FAISS index
- Load FAISS index

Saved files:

 
backend/assets/rag/jarvis_docs.faiss
backend/assets/rag/jarvis_docs.pkl
```

---

## retriever.py

### Purpose

Searches the RAG index.

### Responsibilities

- Load FAISS index
- Embed user questions
- Search documentation vectors
- Filter results by score
- Return matching documentation chunks

This file is not just a test file. It is the core retrieval layer used by the RAG Knowledge Engine.

---

## rag_answer.py

### Purpose

Generates answers from retrieved documentation.

### Responsibilities

- Retrieve relevant docs
- Build documentation context
- Send prompt to local LLM
- Return a voice-friendly response

Recommended improvement:

The system prompt should explicitly say to answer only from the provided documentation.

---

## rag_intent.py

### Purpose

Allows the Intent Router to use RAG as a Jarvis self-knowledge handler.

### Responsibilities

- Decide whether a request is about Jarvis documentation
- Use retrieval score as the intent signal
- Route matching requests to the RAG answer service

---

# Python Files

 
backend/modules/rag/

__init__.py

build_index.py

rag_store.py

retriever.py

rag_answer.py

rag_intent.py
```

---

# Python Packages

Vector Search

- faiss-cpu

Embeddings

- sentence-transformers

Filesystem

- pathlib

Serialization

- pickle

Pattern Matching

- re

Internal Modules

- local_llm
- rag_store
- retriever

---

# Dependencies

Required

- Local LLM
- Ollama
- Markdown docs folder
- sentence-transformers
- faiss-cpu

Optional

- Beast Mode GPU acceleration

RAG should remain part of the standard install because it works well on CPU.

---

# Configuration

Recommended `.env` settings:

```env
RAG_TOP_K=3
RAG_MIN_SCORE=0.70
```

Recommended `jarvis_config.py` values:

```python
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.70"))
```

Use these instead of hardcoding values inside RAG modules.

---

# Index Storage

The RAG index is saved here:

 
backend/assets/rag/

jarvis_docs.faiss

jarvis_docs.pkl
```

`jarvis_docs.faiss` stores the vector index.

`jarvis_docs.pkl` stores metadata for each chunk, including source file, heading, and text.

---

# Recommended Code Improvements

## Use Config Values

Current code hardcodes values such as:

```python
top_k=3
MIN_KNOWLEDGE_SCORE = 0.70
```

Recommended:

```python
from backend.config.jarvis_config import RAG_TOP_K, RAG_MIN_SCORE
```

Then use:

```python
chunks = retrieve_docs(
    command,
    top_k=3,
    min_score=.70,
)
```

---




# Design Decisions

## Why RAG?

RAG allows Jarvis to answer questions about itself without retraining an LLM.

Updating Jarvis knowledge only requires editing Markdown files and rebuilding the index.

---

## Why Markdown Docs?

Markdown is easy for humans to write, easy for AI to parse, and works well for GitHub documentation.

---

## Why FAISS?

FAISS is fast, local, free, and works well for small to medium documentation indexes.

---

## Why Sentence Transformers?

Sentence Transformers provides high-quality semantic embeddings that work locally and do not require a cloud API.

---

## Why Keep RAG CPU-Friendly?

RAG searches are fast even on CPU.

Keeping RAG CPU-compatible avoids unnecessary CUDA installation complexity.

---

# Error Handling

The RAG system should handle:

- Missing docs folder
- Empty docs folder
- Missing FAISS index
- Missing metadata file
- Low-confidence retrieval
- Ollama failures
- Empty answers

If no documentation is found, Jarvis should fall back gracefully.

---


# Related Documentation


- local_llm.md
- intent_router.md
- memory.md
- research.md
- configuration.md
- installation.md
