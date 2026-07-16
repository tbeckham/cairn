# RAG

Local RAG setup using LlamaIndex + Qdrant + LM Studio.

## Collections
- `work` — professional documents
- `personal` — personal documents

## Usage

```bash
# Start Qdrant
podman start qdrant

# Ingest a collection
uv run scripts/ingest.py --collection work

# Watch a folder for changes
uv run scripts/watch.py --collection work

# Query from CLI
uv run scripts/query.py --collection work "your question here"
```

## Setup
See setup steps in project history.
