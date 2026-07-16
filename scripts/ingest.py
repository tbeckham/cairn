#!/usr/bin/env python
"""
Ingest documents from a corpus folder into Qdrant.

Usage:
    uv run scripts/ingest.py --collection work
    uv run scripts/ingest.py --collection personal
    uv run scripts/ingest.py --collection work --collection personal
"""
import argparse
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import COLLECTIONS
from rag.pipeline import ingest


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into RAG collections")
    parser.add_argument(
        "--collection",
        action="append",
        choices=list(COLLECTIONS.keys()),
        required=True,
        metavar="COLLECTION",
        help=f"Collection to ingest. Can be specified multiple times. Choices: {list(COLLECTIONS.keys())}",
    )
    args = parser.parse_args()

    for collection_key in args.collection:
        print(f"\n--- Ingesting '{collection_key}' ---")
        try:
            ingest(collection_key)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error ingesting '{collection_key}': {e}")
            sys.exit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
