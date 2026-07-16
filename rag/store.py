from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from llama_index.vector_stores.qdrant import QdrantVectorStore

from config.settings import QDRANT_HOST, QDRANT_PORT, COLLECTIONS

# Dimension must match the embedding model output (nomic-embed-text-v1.5 = 768)
EMBEDDING_DIM = 768


def get_client() -> QdrantClient:
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def ensure_collections(client: QdrantClient) -> None:
    """Create work and personal collections if they don't already exist."""
    existing = {c.name for c in client.get_collections().collections}

    for key, cfg in COLLECTIONS.items():
        name = cfg["name"]
        if name not in existing:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIM,
                    distance=Distance.COSINE,
                ),
            )
            print(f"Created collection: {name}")
        else:
            print(f"Collection already exists: {name}")


def get_vector_store(collection_name: str, client: QdrantClient) -> QdrantVectorStore:
    """Return a LlamaIndex vector store bound to a specific collection."""
    return QdrantVectorStore(
        collection_name=collection_name,
        client=client,
    )
