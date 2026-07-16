#!/usr/bin/env python
"""
Watch a corpus folder and auto-ingest files when they are created or modified.

Usage:
    uv run scripts/watch.py --collection work
    uv run scripts/watch.py --collection personal

Press Ctrl+C to stop.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from config.settings import COLLECTIONS, SUPPORTED_EXTENSIONS
from rag.pipeline import ingest


class CorpusEventHandler(FileSystemEventHandler):
    def __init__(self, collection_key: str):
        self.collection_key = collection_key
        super().__init__()

    def _is_supported(self, path: str) -> bool:
        return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS

    def _handle(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        if not self._is_supported(event.src_path):
            return
        print(f"\n[watch] Detected change: {event.src_path}")
        print(f"[watch] Re-ingesting '{self.collection_key}'...")
        try:
            ingest(self.collection_key)
            print(f"[watch] Ingest complete.")
        except Exception as e:
            print(f"[watch] Ingest error: {e}")

    def on_created(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._handle(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        # Treat a move/rename into the folder as a new file
        if not event.is_directory and self._is_supported(event.dest_path):
            print(f"\n[watch] File moved in: {event.dest_path}")
            print(f"[watch] Re-ingesting '{self.collection_key}'...")
            try:
                ingest(self.collection_key)
                print(f"[watch] Ingest complete.")
            except Exception as e:
                print(f"[watch] Ingest error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Watch a corpus folder and auto-ingest on changes")
    parser.add_argument(
        "--collection",
        choices=list(COLLECTIONS.keys()),
        required=True,
        help=f"Collection to watch. Choices: {list(COLLECTIONS.keys())}",
    )
    args = parser.parse_args()

    corpus_path = COLLECTIONS[args.collection]["corpus_path"]

    if not corpus_path.exists():
        print(f"Error: corpus path does not exist: {corpus_path}")
        sys.exit(1)

    print(f"[watch] Watching '{corpus_path}' for changes...")
    print(f"[watch] Collection: '{args.collection}'")
    print(f"[watch] Supported extensions: {SUPPORTED_EXTENSIONS}")
    print(f"[watch] Press Ctrl+C to stop.\n")

    handler = CorpusEventHandler(collection_key=args.collection)
    observer = Observer()
    observer.schedule(handler, path=str(corpus_path), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[watch] Stopping...")
        observer.stop()

    observer.join()
    print("[watch] Stopped.")


if __name__ == "__main__":
    main()
