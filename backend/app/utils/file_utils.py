import os
from pathlib import Path


def get_extension(filename: str) -> str:
    """Return the lowercase file extension without the dot."""
    return Path(filename).suffix.lstrip(".").lower()


def safe_filename(filename: str) -> str:
    """Strip directory components and replace spaces."""
    return os.path.basename(filename).replace(" ", "_")
