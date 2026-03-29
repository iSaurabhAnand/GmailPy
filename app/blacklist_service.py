from __future__ import annotations

from pathlib import Path
from typing import Set

from app.config import BLACKLIST_FILE


def _blacklist_path() -> Path:
    return Path(BLACKLIST_FILE)


def load_blacklisted_subjects() -> Set[str]:
    """Load normalized blacklisted subjects from disk."""
    path = _blacklist_path()
    if not path.exists():
        return set()

    return {
        line.strip().casefold()
        for line in path.read_text(encoding='utf-8').splitlines()
        if line.strip()
    }


def is_subject_blacklisted(subject: str, blacklist: Set[str] | None = None) -> bool:
    """Check whether a subject is in the blacklist."""
    normalized_subject = subject.strip().casefold()
    if not normalized_subject:
        return False

    if blacklist is None:
        blacklist = load_blacklisted_subjects()
    return normalized_subject in blacklist


def add_subject_to_blacklist(subject: str) -> bool:
    """Persist a subject to the flat-file blacklist if it is not already present."""
    normalized_subject = subject.strip()
    if not normalized_subject:
        raise ValueError('Subject cannot be empty.')

    blacklist = load_blacklisted_subjects()
    if normalized_subject.casefold() in blacklist:
        return False

    path = _blacklist_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open('a', encoding='utf-8') as blacklist_file:
        blacklist_file.write(f"{normalized_subject}\n")

    return True
