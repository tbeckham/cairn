from pathlib import Path

from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter

from config.settings import CHUNK_OVERLAP, CHUNK_SIZE, SUPPORTED_EXTENSIONS
from rag.sources.registry import Source, matches_extensions
from rag.store import ensure_collections, get_client, get_vector_store


def ingest_folder(source: Source) -> int:
    """
    Ingest all supported documents from a folder source.

    Returns the number of chunks ingested.
    """
    corpus_path: Path = source.path

    if not corpus_path.exists():
        raise FileNotFoundError(f"[{source.name}] Path does not exist: {corpus_path}")

    patterns = set(source.extensions) if source.extensions else SUPPORTED_EXTENSIONS
    supported_files = [
        f for f in corpus_path.rglob("*")
        if f.is_file() and matches_extensions(f, patterns)
    ]

    if not supported_files:
        print(f"[{source.name}] No supported files found in {corpus_path}")
        return 0

    print(f"[{source.name}] Found {len(supported_files)} file(s)")

    client = get_client()
    ensure_collections(client)

    documents = SimpleDirectoryReader(
        input_dir=str(corpus_path),
        required_exts=list(extensions),
        recursive=True,
        filename_as_id=True,
    ).load_data()

    for doc in documents:
        abs_path = doc.metadata.get("file_path", "")
        if abs_path:
            doc.metadata["relative_path"] = str(Path(abs_path).relative_to(corpus_path))
        doc.metadata["source_name"] = source.name
        doc.metadata["collection"] = source.collection

    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    nodes = splitter.get_nodes_from_documents(documents)
    print(f"[{source.name}] Split into {len(nodes)} chunk(s)")

    vector_store = get_vector_store(source.collection, client)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    VectorStoreIndex(nodes=nodes, storage_context=storage_context)

    print(f"[{source.name}] Ingested {len(nodes)} chunk(s) into '{source.collection}'")
    return len(nodes)
