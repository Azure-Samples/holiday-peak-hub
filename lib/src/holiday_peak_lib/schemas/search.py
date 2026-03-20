"""Search schema compatibility exports.

Canonical definitions for these models live in ``truth.py`` to avoid
cross-module duplication.
"""

from .truth import IntentClassification, SearchEnrichedProduct

__all__ = ["IntentClassification", "SearchEnrichedProduct"]
