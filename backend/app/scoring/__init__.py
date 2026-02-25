"""
MMIP Scoring Package

Provides the 5-axis scoring engine and hit prediction algorithm for the
Manga Market Intelligence Platform.

Public API:
    ScoringEngine  - Computes 5-axis composite scores for manga titles.
    HitPredictor   - Generates ranked hit-prediction lists for publishers.
"""

from app.scoring.engine import ScoringEngine
from app.scoring.predictions import HitPredictor

__all__ = ["ScoringEngine", "HitPredictor"]
