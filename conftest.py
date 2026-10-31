"""Pytest configuration: add project root to sys.path."""
import sys
from pathlib import Path

# Ensure the finance-coach root (this file's parent) is importable
sys.path.insert(0, str(Path(__file__).parent))
