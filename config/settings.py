from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# Project root (one level up from config/)
ROOT = Path(__file__).parent.parent

# LM Studio
LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_EMBEDDING_MODEL = os.getenv("LMSTUDIO_EMBEDDING_MODEL", "text-embedding-nomic-embed-text-v1.5")

# Qdrant
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Collections
COLLECTION_WORK = os.getenv("COLLECTION_WORK", "work")
COLLECTION_PERSONAL = os.getenv("COLLECTION_PERSONAL", "personal")

COLLECTIONS = {
    "work": {
        "name": COLLECTION_WORK,
        "corpus_path": ROOT / os.getenv("CORPUS_WORK", "corpus/work"),
    },
    "personal": {
        "name": COLLECTION_PERSONAL,
        "corpus_path": ROOT / os.getenv("CORPUS_PERSONAL", "corpus/personal"),
    },
}

# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "64"))

# Supported file extensions for ingest
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".rst", ".html"}
