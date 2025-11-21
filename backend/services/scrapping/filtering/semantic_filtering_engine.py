from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger
from sklearn.metrics.pairwise import cosine_similarity

from backend.services.scrapping.base_plugin import Event
from backend.services.scrapping.embedding.embedding_engine import (
    get_embedding_instance,
)


class SemanticFilteringEngine:
    """Semantic content filter to determine article relevance.

    This engine uses text embeddings and cosine similarity to assess whether
    incoming articles are relevant with respect to a provided set of reference
    keywords. Compared to keyword-only filters, semantic similarity allows the
    detection of related content even when exact keywords do not appear.

    The workflow is:
    1. Pre-compute embeddings for the reference keywords.
    2. Compute an embedding for each article (title and text body).
    3. Compute cosine similarity between the article and all keyword embeddings.
    4. Keep or filter the article based on a similarity threshold.

    Attributes:
      embedding_engine: Embedding engine used to generate text embeddings.
      keywords_list: List of reference keywords used for relevance.
      keywords_embeddings: Pre-computed embeddings of the reference keywords.
      threshold: Cosine-similarity threshold for relevance decisions.
    """

    def __init__(self, threshold: float, keywords_list: List[str]) -> None:
        """Initialize the semantic filter.

        Args:
          threshold: Cosine similarity threshold for relevance decisions.
          keywords_list: Reference keywords used to gauge semantic similarity.
        """
        # Initialize the embedding engine used to generate embeddings.
        self.embedding_engine = get_embedding_instance()

        # Store provided configuration.
        self.keywords_list = keywords_list
        self.threshold = threshold

        # Pre-compute embeddings for the reference keywords to avoid recomputation.
        logger.info(
            "Pre-computing embeddings for {} reference keywords...",
            len(self.keywords_list),
        )
        self.keywords_embeddings: Optional[np.ndarray] = self._precompute_keywords_embeddings()

        logger.info(
            "SemanticFilteringEngine initialized | threshold={} | keywords={}",
            self.threshold,
            len(self.keywords_list),
        )

    def _precompute_keywords_embeddings(self) -> Optional[np.ndarray]:
        """Pre-compute embeddings for all reference keywords.

        Returns:
          A 2D numpy array of shape `(num_keywords, embedding_dim)` containing
          embeddings for the reference keywords, or `None` if an error occurs.
        """
        try:
            # Compute an embedding for each keyword and stack them into an array.
            embeddings: List[np.ndarray] = []
            for keyword in self.keywords_list:
                embedding = self.embedding_engine.text_to_embedding(keyword)
                embeddings.append(embedding)

            if not embeddings:
                return np.empty((0, 0))

            return np.array(embeddings)
        except Exception as exc:
            logger.error("Error pre-computing keyword embeddings: {}", exc)
            return None

    def is_article_relevant(self, article: Event) -> bool:
        """Check whether an article is relevant using semantic similarity.

        The method embeds the combined article title and body text, computes cosine
        similarity against all pre-computed keyword embeddings, and compares the
        maximum similarity to the configured threshold.

        Args:
          article: Event produced by a scraping plugin.

        Returns:
          True if the maximum cosine similarity with any keyword embedding is
          greater than or equal to the threshold; False otherwise. Returns True
          on failure as a fail-safe to avoid over-filtering.
        """
        safe_title = (article.title or "").strip()
        try:
            # Prepare the article text by combining title and body.
            article_text = self._prepare_article_text(article)

            # Convert article text to an embedding vector and ensure 2D shape.
            article_embedding = self.embedding_engine.text_to_embedding(article_text)
            article_embedding = np.array([article_embedding])  # Shape: (1, embedding_dim)

            # Guard against missing or empty keyword embeddings.
            if self.keywords_embeddings is None or self.keywords_embeddings.size == 0:
                logger.warning(
                    "No keyword embeddings available; defaulting to keep article '{}'",
                    safe_title,
                )
                return True

            # Compute cosine similarities and obtain the maximum score.
            cosine_scores = cosine_similarity(article_embedding, self.keywords_embeddings)
            max_score = float(cosine_scores.max())

            # Compare to threshold to make a relevance decision.
            is_relevant = max_score >= self.threshold

            logger.info(
                "Article '{}' | similarity={:.3f} | relevant={}",
                safe_title,
                max_score,
                is_relevant,
            )
            return is_relevant

        except Exception as exc:
            logger.error(
                "Error in semantic filtering for article '{}' : {}",
                safe_title,
                exc,
            )
            # Fail-safe: consider article relevant if an error occurs.
            return True

    def get_filter_explanation(self, article: Event) -> Dict[str, Any]:
        """Provide details that explain the relevance decision.

        Args:
          article: Event produced by a scraping plugin.

        Returns:
          A dictionary containing the article title, the maximum cosine similarity
          score, the best-matching reference keyword, the threshold, and the final
          decision. On failure, returns a fail-safe response with `decision='KEEP'`.
        """
        safe_title = (article.title or "").strip()
        try:
            # Prepare the text and embed it.
            article_text = self._prepare_article_text(article)
            article_embedding = self.embedding_engine.text_to_embedding(article_text)
            article_embedding = np.array([article_embedding])

            # Guard against missing or empty keyword embeddings.
            if self.keywords_embeddings is None or self.keywords_embeddings.size == 0:
                return {
                    "article_title": safe_title,
                    "max_similarity_score": 0.0,
                    "matched_reference_keyword": None,
                    "threshold": self.threshold,
                    "is_relevant": True,
                    "decision": "KEEP",
                    "note": "No keyword embeddings available.",
                }

            # Compute cosine similarity vector and flatten to 1D.
            cosine_scores = cosine_similarity(article_embedding, self.keywords_embeddings)
            cosine_scores = cosine_scores.flatten()

            # Identify best matching keyword and its score.
            max_score = float(cosine_scores.max())
            max_idx = int(cosine_scores.argmax())
            matched_keyword = self.keywords_list[max_idx]

            # Threshold decision.
            is_relevant = max_score >= self.threshold

            return {
                "article_title": safe_title,
                "max_similarity_score": round(max_score, 3),
                "matched_reference_keyword": matched_keyword,
                "threshold": self.threshold,
                "is_relevant": is_relevant,
                "decision": "KEEP" if is_relevant else "FILTER_OUT",
            }

        except Exception as exc:
            logger.error(
                "Error in get_filter_explanation for article '{}' : {}",
                safe_title,
                exc,
            )
            return {
                "article_title": safe_title,
                "max_similarity_score": 0.0,
                "matched_reference_keyword": None,
                "threshold": self.threshold,
                "is_relevant": True,  # Fail safe
                "decision": "KEEP",
                "error": str(exc),
            }

    def _prepare_article_text(self, article: Event) -> str:
        """Combine article title and text into a single string.

        Args:
          article: Event emitted by a scraping plugin.

        Returns:
          Combined text of title and body text, or an empty string when missing.
        """
        title = (article.title or "").strip()
        text = (article.text or "").strip()

        # Prefer "title + text" when both are present, otherwise fall back.
        if title and text:
            return f"{title} {text}"
        if title:
            return title
        if text:
            return text
        return ""

    def update_threshold(self, threshold: float) -> None:
        """Update the relevance threshold.

        Args:
          threshold: New cosine similarity threshold to apply.
        """
        # Replace the threshold used for future relevance decisions.
        self.threshold = threshold

    def get_performance_stats(self) -> Dict[str, Any]:
        """Return performance and configuration information.

        Returns:
          A dictionary with counts, embedding availability, embedding dimension,
          and the active threshold.
        """
        # Derive the embedding dimension if embeddings are available.
        embedding_dim = (
            int(self.keywords_embeddings.shape[1])
            if self.keywords_embeddings is not None and self.keywords_embeddings.size
            else 0
        )

        return {
            "reference_keywords_count": len(self.keywords_list),
            "precomputed_embeddings": self.keywords_embeddings is not None,
            "embedding_dimension": embedding_dim,
            "threshold": self.threshold,
        }
