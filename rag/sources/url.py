import hashlib
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter

from config.settings import CHUNK_OVERLAP, CHUNK_SIZE
from rag.sources.registry import Source
from rag.store import ensure_collections, get_client, get_vector_store

# Tags whose content we discard entirely
SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "form"}


def _fetch_text(url: str, timeout: int = 15) -> str:
    """Fetch a URL and return clean plain text."""
    headers = {"User-Agent": "cairn-rag/1.0 (local knowledge indexer)"}
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(SKIP_TAGS):
        tag.decompose()

    text = soup.get_text(separator="\n")
    # Collapse runs of blank lines
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _discover_links(base_url: str, html: str, same_domain_only: bool = True) -> list[str]:
    """Extract all hrefs from a page, optionally filtered to the same domain."""
    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(base_url).netloc
    links = set()

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if parsed.scheme not in ("http", "https"):
            continue
        if same_domain_only and parsed.netloc != base_domain:
            continue
        # Strip anchors
        links.add(parsed._replace(fragment="").geturl())

    return sorted(links)


def _url_to_doc_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def ingest_url(source: Source, crawl: bool = False, max_pages: int = 20) -> int:
    """
    Fetch and ingest a URL (and optionally crawl same-domain links).

    Args:
        source:    the Source definition (source.url must be set)
        crawl:     if True, follow same-domain links found on the page
        max_pages: maximum pages to crawl (ignored if crawl=False)

    Returns the number of chunks ingested.
    """
    start_url: str = source.url

    headers = {"User-Agent": "cairn-rag/1.0 (local knowledge indexer)"}

    urls_to_visit = [start_url]
    visited: set[str] = set()
    documents: list[Document] = []

    while urls_to_visit and len(visited) < max_pages:
        url = urls_to_visit.pop(0)
        if url in visited:
            continue

        print(f"[{source.name}] Fetching: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"[{source.name}] Skipping {url}: {e}")
            visited.add(url)
            continue

        visited.add(url)
        raw_html = response.text

        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(SKIP_TAGS):
            tag.decompose()
        text = re.sub(r"\n{3,}", "\n\n", soup.get_text(separator="\n")).strip()

        if text:
            documents.append(Document(
                text=text,
                doc_id=_url_to_doc_id(url),
                metadata={
                    "source_name": source.name,
                    "collection": source.collection,
                    "relative_path": urlparse(url).path or "/",
                    "url": url,
                },
            ))

        if crawl:
            new_links = _discover_links(url, raw_html)
            for link in new_links:
                if link not in visited and link not in urls_to_visit:
                    urls_to_visit.append(link)

    if not documents:
        print(f"[{source.name}] No content extracted from {start_url}")
        return 0

    print(f"[{source.name}] Fetched {len(documents)} page(s)")

    client = get_client()
    ensure_collections(client)

    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    nodes = splitter.get_nodes_from_documents(documents)
    print(f"[{source.name}] Split into {len(nodes)} chunk(s)")

    vector_store = get_vector_store(source.collection, client)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    VectorStoreIndex(nodes=nodes, storage_context=storage_context)

    print(f"[{source.name}] Ingested {len(nodes)} chunk(s) into '{source.collection}'")
    return len(nodes)
