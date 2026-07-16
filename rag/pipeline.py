from pathlib import Path

from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    Settings,
)
from llama_index.core.node_parser import SentenceSplitter
from qdrant_client import QdrantClient

from config.settings import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    COLLECTIONS,
    SUPPORTED_EXTENSIONS,
)
from rag.embedder import get_embedder
from rag.store import get_client, ensure_collections, get_vector_store


def _configure_llamaindex(embedder) -> None:
    """Set LlamaIndex global settings so no OpenAI calls are made implicitly."""
    Settings.embed_model = embedder
    Settings.llm = None


def _get_index(collection_name: str, client: QdrantClient) -> VectorStoreIndex:
    vector_store = get_vector_store(collection_name, client)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
    )


def ingest(collection_key: str) -> None:
    """
    Ingest all supported documents from a corpus folder into the
    corresponding Qdrant collection.

    Args:
        collection_key: 'work' or 'personal'
    """
    if collection_key not in COLLECTIONS:
        raise ValueError(f"Unknown collection: '{collection_key}'. Choose from {list(COLLECTIONS.keys())}")

    cfg = COLLECTIONS[collection_key]
    corpus_path: Path = cfg["corpus_path"]
    collection_name: str = cfg["name"]

    if not corpus_path.exists():
        raise FileNotFoundError(f"Corpus path does not exist: {corpus_path}")

    supported_files = [
        f for f in corpus_path.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not supported_files:
        print(f"No supported files found in {corpus_path}")
        print(f"Supported extensions: {SUPPORTED_EXTENSIONS}")
        return

    print(f"Found {len(supported_files)} file(s) to ingest into '{collection_name}'")

    embedder = get_embedder()
    _configure_llamaindex(embedder)

    client = get_client()
    ensure_collections(client)

    documents = SimpleDirectoryReader(
        input_dir=str(corpus_path),
        required_exts=list(SUPPORTED_EXTENSIONS),
        recursive=True,
        filename_as_id=True,
    ).load_data()

    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    nodes = splitter.get_nodes_from_documents(documents)
    print(f"Split into {len(nodes)} chunk(s)")

    vector_store = get_vector_store(collection_name, client)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
    )

    print(f"Ingested {len(nodes)} chunk(s) into '{collection_name}'")


def query(collection_key: str, question: str, top_k: int = 5) -> list[dict]:
    """
    Query a collection and return the top-k most relevant chunks.

    Args:
        collection_key: 'work' or 'personal'
        question: natural language query string
        top_k: number of results to return

    Returns:
        List of dicts with 'text', 'score', and 'source' keys
    """
    if collection_key not in COLLECTIONS:
        raise ValueError(f"Unknown collection: '{collection_key}'. Choose from {list(COLLECTIONS.keys())}")

    collection_name = COLLECTIONS[collection_key]["name"]

    embedder = get_embedder()
    _configure_llamaindex(embedder)

    client = get_client()
    index = _get_index(collection_name, client)

    retriever = index.as_retriever(similarity_top_k=top_k)
    results = retriever.retrieve(question)

    return [
        {
            "score": round(node.score, 4) if node.score else None,
            "source": node.metadata.get("file_name", "unknown"),
            "text": node.text.strip(),
        }
        for node in results
    ]
