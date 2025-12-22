"""
thumbnail_cache.py

Handles loading and caching of image thumbnails to improve performance
in thumbnail browsing interfaces. Uses file modification time and path
to generate a stable cache key.
"""

import os
import hashlib
from pathlib import Path
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

def get_thumbnail_cache_dir() -> Path:
    """
    Return the platform-specific thumbnail cache directory.
    Follows XDG Base Directory specification on Linux; falls back to ~/.cache/qiv/thumbnails.
    """
    cache_home = os.environ.get("XDG_CACHE_HOME")
    if not cache_home:
        cache_home = os.path.expanduser("~/.cache")
    return Path(cache_home) / "qiv" / "thumbnails"

def get_cache_path(file_path: str) -> Path:
    """
    Generate a unique cache file path based on the original file path and its modification time.
    This ensures the cache is automatically invalidated when the file changes.
    """
    stat = os.stat(file_path)
    key = f"{file_path}_{stat.st_mtime}"
    hash_key = hashlib.md5(key.encode()).hexdigest()
    return get_thumbnail_cache_dir() / f"{hash_key}.jpg"

def load_or_create_thumbnail(path: str) -> QPixmap | None:
    """
    Load a thumbnail from cache if available; otherwise, generate a new one,
    save it to the cache, and return it. Returns None if the image cannot be loaded.
    """
    cache_path = get_cache_path(path)
    if cache_path.exists():
        return QPixmap(str(cache_path))
    pixmap = QPixmap(path)
    if pixmap.isNull():
        return None

    # Scale to 256px max dimension while preserving aspect ratio
    thumb = pixmap.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # Ensure cache directory exists
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    # Save to cache as JPEG (80% quality)
    thumb.save(str(cache_path), "JPEG", 80)
    return thumb