import subprocess
from pathlib import Path

from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter

from config.settings import CHUNK_OVERLAP, CHUNK_SIZE
from rag.sources.registry import Source, matches_extensions
from rag.store import ensure_collections, get_client, get_vector_store

DEFAULT_GIT_EXTENSIONS = {".md", ".txt", ".rst", ".py", ".sh", ".yaml", ".yml", ".toml", ".json"}

# Folders and files to always skip in git repos
EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", "dist", "build", ".mypy_cache", ".ruff_cache"}
EXCLUDED_FILES = {"uv.lock", "package-lock.json", "yarn.lock", "poetry.lock", "Pipfile.lock"}


def _git_pull(path: Path, source_name: str) -> bool:
    """
    Run git pull in the repo directory.
    Returns True if changes were pulled, False if already up to date.
    """
    try:
        result = subprocess.run(
            ["git", "pull"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"[{source_name}] git pull failed: {result.stderr.strip()}")
            return False

        output = result.stdout.strip()
        print(f"[{source_name}] git pull: {output}")
        return "Already up to date" not in output

    except subprocess.TimeoutExpired:
        print(f"[{source_name}] git pull timed out")
        return False
    except FileNotFoundError:
        print(f"[{source_name}] git not found in PATH")
        return False


def ingest_git(source: Source, pull: bool = True) -> int:
    """
    Ingest supported files from a local git repository.

    Args:
        source: the Source definition
        pull:   if True, run git pull before ingesting

    Returns the number of chunks ingested.
    """
    repo_path: Path = source.path

    if not repo_path.exists():
        raise FileNotFoundError(f"[{source.name}] Repo path does not exist: {repo_path}")

    if not (repo_path / ".git").exists():
        raise ValueError(f"[{source.name}] Not a git repository: {repo_path}")

    if pull:
        _git_pull(repo_path, source.name)

    patterns = set(source.extensions) if source.extensions else DEFAULT_GIT_EXTENSIONS
    supported_files = [
        f for f in repo_path.rglob("*")
        if f.is_file()
        and matches_extensions(f, patterns)
        and not any(part in EXCLUDED_DIRS for part in f.parts)
        and f.name not in EXCLUDED_FILES
    ]

    if not supported_files:
        print(f"[{source.name}] No supported files found in {repo_path}")
        return 0

    print(f"[{source.name}] Found {len(supported_files)} file(s) in {repo_path}")

    client = get_client()
    ensure_collections(client)

    documents = SimpleDirectoryReader(
        input_files=[str(f) for f in supported_files],
        filename_as_id=True,
    ).load_data()

    for doc in documents:
        abs_path = doc.metadata.get("file_path", "")
        if abs_path:
            doc.metadata["relative_path"] = str(Path(abs_path).relative_to(repo_path))
        doc.metadata["source_name"] = source.name
        doc.metadata["collection"] = source.collection
        doc.metadata["repo"] = str(repo_path)

    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    nodes = splitter.get_nodes_from_documents(documents)
    print(f"[{source.name}] Split into {len(nodes)} chunk(s)")

    vector_store = get_vector_store(source.collection, client)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    VectorStoreIndex(nodes=nodes, storage_context=storage_context)

    print(f"[{source.name}] Ingested {len(nodes)} chunk(s) into '{source.collection}'")
    return len(nodes)
