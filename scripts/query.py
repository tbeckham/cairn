#!/usr/bin/env python
"""
Query a RAG collection from the CLI.

Usage:
    uv run scripts/query.py --collection work "your question here"
    uv run scripts/query.py --collection personal --top-k 3 "your question here"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import COLLECTIONS
from rag.pipeline import query


def main():
    parser = argparse.ArgumentParser(description="Query a RAG collection")
    parser.add_argument(
        "--collection",
        choices=list(COLLECTIONS.keys()),
        required=True,
        help=f"Collection to query. Choices: {list(COLLECTIONS.keys())}",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results to return (default: 5)",
    )
    parser.add_argument(
        "question",
        type=str,
        help="The question or search query",
    )
    args = parser.parse_args()

    print(f"\nQuerying '{args.collection}' for: {args.question!r}\n")

    try:
        results = query(args.collection, args.question, top_k=args.top_k)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    if not results:
        print("No results found.")
        return

    for i, result in enumerate(results, 1):
        print(f"--- Result {i} (score: {result['score']}) ---")
        print(f"Source: {result['source']}")
        print(f"{result['text']}")
        print()


if __name__ == "__main__":
    main()
