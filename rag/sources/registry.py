"""
Source registry — loads and validates sources.yaml.

A source definition has:
  name        (str, required)   unique identifier
  type        (str, required)   folder | git | url
  collection  (str, required)   work | personal
  watch       (bool, optional)  auto-watch for changes (folder/git only)
  schedule    (str, optional)   cron string for scheduled sync (url/any)
  path        (str, optional)   local path — required for folder and git types
  url         (str, optional)   URL — required for url type
  extensions  (list, optional)  file extensions to ingest (git type)
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml

from config.settings import COLLECTIONS

ROOT = Path(__file__).parent.parent.parent
SOURCES_FILE = ROOT / "sources.yaml"
SECRETS_FILE = ROOT / "sources.secrets.yaml"

SourceType = Literal["folder", "git", "url"]
VALID_TYPES: set[str] = {"folder", "git", "url"}


@dataclass
class Source:
    name: str
    type: SourceType
    collection: str
    watch: bool = False
    schedule: str | None = None
    path: Path | None = None
    url: str | None = None
    extensions: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.type not in VALID_TYPES:
            raise ValueError(f"Source '{self.name}': unknown type '{self.type}'. Must be one of {VALID_TYPES}")

        if self.collection not in COLLECTIONS:
            raise ValueError(f"Source '{self.name}': unknown collection '{self.collection}'. Must be one of {list(COLLECTIONS.keys())}")

        if self.type in ("folder", "git"):
            if not self.path:
                raise ValueError(f"Source '{self.name}': type '{self.type}' requires a 'path'")
            self.path = Path(self.path).expanduser().resolve()

        if self.type == "url":
            if not self.url:
                raise ValueError(f"Source '{self.name}': type 'url' requires a 'url'")

        if self.extensions:
            # Normalise entries but preserve wildcards and dotfile names as-is.
            # Examples after normalisation:
            #   "md"      -> ".md"       (plain extension, add dot)
            #   ".py"     -> ".py"       (already dotted, keep)
            #   ".zsh*"   -> ".zsh*"     (wildcard, keep)
            #   ".zshrc"  -> ".zshrc"    (dotfile, keep)
            #   "zsh*"    -> ".zsh*"     (wildcard without dot, add dot)
            normalized = []
            for e in self.extensions:
                if not e.startswith("."):
                    e = f".{e}"
                normalized.append(e)
            self.extensions = normalized


def matches_extensions(path: Path, patterns: set[str]) -> bool:
    """
    Return True if a file path matches any of the extension patterns.

    Patterns support:
      - Exact suffixes:  ".py", ".md"
      - Wildcards:       ".zsh*", ".env*"
      - Dotfiles:        ".zshrc", ".gitignore" (matched by full filename)
      - No extension:    files like .zshrc have suffix="" so we match by name

    Examples:
      matches_extensions(Path(".zshrc"),        {".zsh*"})   -> True
      matches_extensions(Path("config.py"),     {".py"})     -> True
      matches_extensions(Path("notes.md"),      {".md*"})    -> True
      matches_extensions(Path(".gitignore"),    {".gitignore"}) -> True
    """
    suffix = path.suffix.lower()       # e.g. ".py" or "" for dotfiles
    name   = path.name.lower()         # e.g. ".zshrc"

    for pattern in patterns:
        p = pattern.lower()
        # Wildcard pattern — match against suffix first, then full name
        if "*" in p or "?" in p:
            if fnmatch.fnmatch(suffix, p) or fnmatch.fnmatch(name, p):
                return True
        else:
            # Exact match: suffix for normal files, full name for dotfiles
            if suffix == p or name == p:
                return True
    return False


def _load_yaml(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("sources", [])


def load_sources(sources_file: Path = SOURCES_FILE) -> list[Source]:
    """Load and validate all sources from sources.yaml."""
    raw = _load_yaml(sources_file)
    secrets = {s["name"]: s for s in _load_yaml(SECRETS_FILE)}

    sources = []
    names_seen: set[str] = set()

    for entry in raw:
        name = entry.get("name")
        if not name:
            raise ValueError(f"A source entry is missing a 'name': {entry}")
        if name in names_seen:
            raise ValueError(f"Duplicate source name: '{name}'")
        names_seen.add(name)

        merged = {**entry, **secrets.get(name, {})}

        sources.append(Source(
            name=merged["name"],
            type=merged["type"],
            collection=merged["collection"],
            watch=merged.get("watch", False),
            schedule=merged.get("schedule"),
            path=merged.get("path"),
            url=merged.get("url"),
            extensions=merged.get("extensions", []),
            extra={k: v for k, v in merged.items()
                   if k not in ("name", "type", "collection", "watch", "schedule", "path", "url", "extensions")},
        ))

    return sources


def get_source(name: str) -> Source:
    """Fetch a single source by name, raising if not found."""
    sources = load_sources()
    for source in sources:
        if source.name == name:
            return source
    available = [s.name for s in sources]
    raise ValueError(f"Source '{name}' not found. Available: {available}")
