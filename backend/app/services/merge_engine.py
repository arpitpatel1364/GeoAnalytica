"""
Merge Engine re-export — MergeEngine lives in data_normalizer.py
but is also imported from merge_engine.py for clean imports in tasks.
"""
from app.services.data_normalizer import MergeEngine

__all__ = ["MergeEngine"]
