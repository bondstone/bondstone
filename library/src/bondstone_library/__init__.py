"""Packs, bridges and presets for bondstone. Nothing here is loaded unless a profile names it."""

from pathlib import Path

__version__ = "0.1.0"


def source() -> Path:
    """The folder bondstone searches for this package's packs, bridges and presets."""
    return Path(__file__).parent / "packs"
