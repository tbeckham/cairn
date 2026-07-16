#!/usr/bin/env python
"""
Sync one or more sources defined in sources.yaml into Qdrant.

Usage:
    uv run scripts/sync.py --all
    uv run scripts/sync.py --source work-docs
    uv run scripts/sync.py --source work-docs --source my-repo
    uv run scripts/sync.py --type git
    uv run scripts/sync.py --scheduler
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core import Settings

from rag.embedder import get_embedder
from rag.sources.folder import ingest_folder
from rag.sources.git import ingest_git
from rag.sources.registry import Source, load_sources
from rag.sources.url import ingest_url


def _configure():
    Settings.embed_model = get_embedder()
    Settings.llm = None


def sync_source(source: Source) -> int:
    """Dispatch to the correct ingest function based on source type."""
    if source.type == "folder":
        return ingest_folder(source)
    elif source.type == "git":
        return ingest_git(source, pull=True)
    elif source.type == "url":
        crawl = source.extra.get("crawl", False)
        max_pages = int(source.extra.get("max_pages", 20))
        return ingest_url(source, crawl=crawl, max_pages=max_pages)
    else:
        print(f"[{source.name}] Unknown source type: {source.type}")
        return 0


def run_sync(sources: list[Source]) -> None:
    _configure()
    total_chunks = 0
    errors = []

    for source in sources:
        print(f"\n--- Syncing '{source.name}' (type={source.type}, collection={source.collection}) ---")
        try:
            count = sync_source(source)
            total_chunks += count
        except Exception as e:
            print(f"[{source.name}] Error: {e}")
            errors.append((source.name, str(e)))

    print(f"\nSync complete. Total chunks ingested: {total_chunks}")
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for name, msg in errors:
            print(f"  {name}: {msg}")
        sys.exit(1)


def run_scheduler(sources: list[Source]) -> None:
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduled = [s for s in sources if s.schedule]
    if not scheduled:
        print("No sources with a 'schedule' field found in sources.yaml. Exiting.")
        sys.exit(0)

    _configure()
    scheduler = BlockingScheduler()

    for source in scheduled:
        trigger = CronTrigger.from_crontab(source.schedule)
        scheduler.add_job(
            sync_source,
            trigger=trigger,
            args=[source],
            id=source.name,
            name=f"sync:{source.name}",
        )
        print(f"Scheduled '{source.name}' with cron: {source.schedule}")

    print("\nScheduler running. Press Ctrl+C to stop.\n")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\nScheduler stopped.")


def main():
    all_sources = load_sources()
    source_names = [s.name for s in all_sources]
    source_types = list({s.type for s in all_sources})

    parser = argparse.ArgumentParser(description="Sync sources into cairn RAG collections")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="Sync all sources defined in sources.yaml",
    )
    group.add_argument(
        "--source",
        action="append",
        metavar="NAME",
        help=f"Sync a specific source by name. Can be repeated. Available: {source_names}",
    )
    group.add_argument(
        "--type",
        dest="source_type",
        choices=source_types,
        help="Sync all sources of a given type",
    )
    group.add_argument(
        "--scheduler",
        action="store_true",
        help="Start the background scheduler for sources with a 'schedule' field",
    )

    args = parser.parse_args()

    if args.all:
        targets = all_sources
    elif args.source:
        targets = []
        for name in args.source:
            match = next((s for s in all_sources if s.name == name), None)
            if not match:
                print(f"Error: source '{name}' not found. Available: {source_names}")
                sys.exit(1)
            targets.append(match)
    elif args.source_type:
        targets = [s for s in all_sources if s.type == args.source_type]
        if not targets:
            print(f"No sources of type '{args.source_type}' found.")
            sys.exit(0)
    elif args.scheduler:
        run_scheduler(all_sources)
        return

    run_sync(targets)


if __name__ == "__main__":
    main()
