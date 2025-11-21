"""Unit tests for the semantic filtering engine.

This suite focuses on production-relevant behaviors rather than trivial cases.
We validate threshold logic, best-keyword selection, fail-safe paths on errors,
and robustness to missing embeddings. We stub the embedding engine with
deterministic vectors to avoid heavyweight models and to precisely control
similarity outcomes.
"""

from __future__ import annotations

from typing import Any, Dict, Generator, List

import numpy as np
import pytest
from pytest_mock import MockerFixture

from backend.services.scrapping.base_plugin import Event


class _DeterministicEmbeddingEngine:
    """A minimal, deterministic embedding engine used for testing.

    This stub avoids loading any real models while giving us full control over
    vector outputs and, consequently, cosine similarities. We intentionally keep
    vectors low-dimensional to make expectations and thresholds easy to reason
    about.

    Behavior:
    - Keywords map to orthogonal unit vectors to create clear winners.
    - Articles produce vectors based on the presence of indicative terms.
    - Whitespace-only strings raise ValueError to mirror production guards.
    """

    def __init__(self) -> None:
        # Fixed 3D basis vectors to create distinct semantic axes.
        self._basis = {
            "ai": np.array([1.0, 0.0, 0.0], dtype=np.float32),
            "cloud": np.array([0.0, 1.0, 0.0], dtype=np.float32),
            # Third axis is unused by keywords but helps test dimensionality.
        }

    def text_to_embedding(self, text: str) -> np.ndarray:
        """Return a deterministic embedding for a given text.

        Args:
            text: Input text to embed.

        Returns:
            A 1D numpy vector representing the text.

        Raises:
            ValueError: If `text` is empty or only contains whitespace.
        """
        if text is None or not text.strip():
            raise ValueError("Input text must be non-empty.")

        lower = text.lower()

        # If the text looks like a keyword, return a clean basis vector.
        if lower.strip() == "ai":
            return self._basis["ai"].copy()
        if lower.strip() == "cloud":
            return self._basis["cloud"].copy()

        # Article heuristics: craft vectors that lean toward specific axes.
        if "cloud" in lower or "azure" in lower or "aws" in lower:
            # Strongly cloud-oriented with a small orthogonal component.
            v = np.array([0.1, 0.99, 0.0], dtype=np.float32)
            return v / np.linalg.norm(v)
        if "ai" in lower or "ml" in lower or "model" in lower:
            v = np.array([0.99, 0.1, 0.0], dtype=np.float32)
            return v / np.linalg.norm(v)

        # Ambiguous content that is somewhat balanced across axes.
        v = np.array([0.7, 0.7, 0.0], dtype=np.float32)
        return v / np.linalg.norm(v)


@pytest.fixture(autouse=True)
def patch_embedding_engine(mocker: MockerFixture) -> Generator[None, None, None]:
    """Patch the semantic filter to use a deterministic embedding engine.

    This ensures tests are fast, reproducible, and independent from any
    heavyweight model downloads.
    """
    # Import inside the fixture so that patching works even if other tests
    # import different parts of the backend earlier.
    mocker.patch(
        "backend.services.scrapping.embedding.embedding_engine.get_embedding",
        autospec=True,
    )
    mocker.patch(
        "backend.services.scrapping.embedding.embedding_engine.get_embedding_instance",
        return_value=_DeterministicEmbeddingEngine(),
    )
    yield


def _make_engine(threshold: float, keywords: List[str]):
    """Helper to build the SemanticFilteringEngine under our patches.

    Args:
        threshold: Cosine similarity threshold for relevance.
        keywords: List of reference keywords.

    Returns:
        Instantiated `SemanticFilteringEngine` that uses the deterministic
        embedding engine via our patch.
    """
    from backend.services.scrapping.filtering.semantic_filtering_engine import (
        SemanticFilteringEngine,
    )

    return SemanticFilteringEngine(threshold=threshold, keywords_list=keywords)


def _make_event(*, title: str, text: str) -> Event:
    """Helper to build Event instances for tests."""
    return Event(
        source="test-source",
        source_type="unit-test",
        title=title,
        text=text,
    )


def test_relevance_and_keyword_selection_with_threshold() -> None:
    """Validate threshold logic and best-keyword selection using controlled vectors.

    We configure orthogonal keyword embeddings for "AI" and "Cloud" and craft two
    articles: one strongly cloud-leaning (should be kept), and one ambiguous with
    moderate similarity (should be filtered out at a higher threshold).
    """
    engine = _make_engine(threshold=0.75, keywords=["AI", "Cloud"])

    cloud_article = _make_event(
        title="Case study: Hybrid cloud migration",
        text="Cost optimization and governance in Azure",
    )
    assert engine.is_article_relevant(cloud_article) is True

    explanation = engine.get_filter_explanation(cloud_article)
    assert explanation["matched_reference_keyword"] == "Cloud"
    assert explanation["is_relevant"] is True
    assert explanation["decision"] == "KEEP"
    assert 0.75 <= explanation["max_similarity_score"] <= 1.0

    ambiguous_article = _make_event(
        title="Quarterly update on IT operations",
        text="Cross-team coordination and incident workflows",
    )
    assert engine.is_article_relevant(ambiguous_article) is False
    ambiguous_expl = engine.get_filter_explanation(ambiguous_article)
    assert ambiguous_expl["decision"] == "FILTER_OUT"


def test_fail_safe_on_empty_article_text() -> None:
    """Ensure the engine fails safe (keep) when embedding raises on empty input.

    The `_prepare_article_text` returns an empty string for whitespace-only
    title/summary; our stub raises `ValueError` for such input. The engine must
    catch the error and return `True` to avoid over-filtering in production.
    """
    engine = _make_engine(threshold=0.8, keywords=["AI", "Cloud"])
    article = _make_event(title="   ", text="\n\t")
    assert engine.is_article_relevant(article) is True


def test_no_keyword_embeddings_defaults_to_keep(mocker: MockerFixture) -> None:
    """When keyword embeddings are unavailable, the engine defaults to keep.

    We simulate a failure in pre-computing embeddings. The engine should warn
    and keep the article; `get_filter_explanation` should include a helpful note.
    """
    # Force the precompute method to fail, returning None for embeddings.
    from backend.services.scrapping.filtering import semantic_filtering_engine as sfe

    mocker.patch.object(
        sfe.SemanticFilteringEngine,
        "_precompute_keywords_embeddings",
        return_value=None,
    )

    engine = _make_engine(threshold=0.9, keywords=["AI", "Cloud"])

    article = _make_event(
        title="Cloud pricing updates",
        text="New reserved instance discounts on AWS",
    )
    assert engine.is_article_relevant(article) is True

    expl = engine.get_filter_explanation(article)
    assert expl["decision"] == "KEEP"
    assert expl["note"] == "No keyword embeddings available."


def test_threshold_update_changes_decision() -> None:
    """Verify that adjusting the threshold flips the decision for marginal cases.

    We intentionally avoid texts that map to near-perfect axis alignments. The
    ambiguous article below yields roughly 0.707 cosine similarity to both
    keyword axes in our deterministic stub. It should be filtered at 0.75 and
    then kept after lowering the threshold to 0.69.
    """
    engine = _make_engine(threshold=0.75, keywords=["AI", "Cloud"])
    article = _make_event(
        title="Quarterly IT operations update",
        text="Cross-team coordination and incident workflows",
    )

    # Initially filtered at a strict threshold.
    assert engine.is_article_relevant(article) is False

    # Lower threshold and confirm the decision flips to keep.
    engine.update_threshold(0.69)
    assert engine.is_article_relevant(article) is True


def test_performance_stats_reflect_configuration() -> None:
    """Ensure performance stats capture keyword count, dims, and threshold.

    With two reference keywords and 3D embeddings, stats should reflect the
    precomputed state and surface the current threshold.
    """
    engine = _make_engine(threshold=0.8, keywords=["AI", "Cloud"])
    stats: Dict[str, Any] = engine.get_performance_stats()

    assert stats["reference_keywords_count"] == 2
    assert stats["precomputed_embeddings"] is True
    assert stats["embedding_dimension"] == 3
    assert stats["threshold"] == 0.8


def test_empty_keywords_are_guarded_and_keep_article() -> None:
    """Empty reference keywords should not filter out content by accident.

    The engine precomputes to an empty array, which must trigger the guard in
    both relevance check and explanation paths, defaulting to keep.
    """
    engine = _make_engine(threshold=0.9, keywords=[])

    article = _make_event(
        title="Cloud strategy and TCO",
        text="A CIO guide to migration and governance",
    )

    assert engine.is_article_relevant(article) is True
    expl = engine.get_filter_explanation(article)
    assert expl["decision"] == "KEEP"
    assert expl["matched_reference_keyword"] is None
