#!/usr/bin/env python
"""
Cairn MCP server — exposes RAG query capabilities over the MCP stdio transport.

Usage (Crush / any MCP client):
    uv --directory /path/to/cairn run mcp_server.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP

from config.settings import COLLECTIONS
from rag.pipeline import query as rag_query

mcp = FastMCP("cairn")


@mcp.tool()
def list_collections() -> list[str]:
    """Return the names of all available RAG collections."""
    return list(COLLECTIONS.keys())


@mcp.tool()
def query_rag(collection: str, question: str, top_k: int = 5) -> list[dict]:
    """
    Search a RAG collection and return the most relevant document chunks.

    Args:
        collection: Collection to search — one of the values returned by list_collections.
        question:   Natural-language query string.
        top_k:      Number of chunks to return (default 5).

    Returns:
        List of dicts, each with keys: score (float), source (filename), text (str).
    """
    if collection not in COLLECTIONS:
        raise ValueError(
            f"Unknown collection '{collection}'. "
            f"Available: {list(COLLECTIONS.keys())}"
        )
    return rag_query(collection, question, top_k=top_k)


if __name__ == "__main__":
    mcp.run(transport="stdio")
