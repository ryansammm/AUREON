"""Shared fixtures for AUREON engine tests."""

import sys
from pathlib import Path

import pytest

# Ensure engine package is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.config_loader import load_genre_config, CONFIG_DIR


@pytest.fixture
def house_config():
    """Load the house genre config."""
    return load_genre_config("house")


@pytest.fixture
def techno_config():
    """Load the techno genre config."""
    return load_genre_config("techno")


@pytest.fixture
def dubstep_config():
    """Load the dubstep genre config."""
    return load_genre_config("dubstep")


@pytest.fixture
def dnb_config():
    """Load the drum_and_bass genre config."""
    return load_genre_config("drum_and_bass")


@pytest.fixture
def generic_config():
    """Load the generic (fallback) genre config."""
    return load_genre_config("generic")
