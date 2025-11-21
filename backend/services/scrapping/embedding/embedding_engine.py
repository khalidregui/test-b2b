from functools import lru_cache

import numpy as np
from dotenv import load_dotenv
from loguru import logger
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()


class EmbeddingEngine:
    """Provides utilities to generate text embeddings.

    Attributes:
        model_name (str): Name of the SentenceTransformer model to load.
        model (SentenceTransformer): Loaded SentenceTransformer model instance.
        normalize_embeddings (bool): Flag indicating whether to L2-normalize embeddings.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        normalize_embeddings: bool = True,
    ) -> None:
        # Persist configuration to allow multiple engines with different settings.
        self.model_name = model_name
        self.model = EmbeddingEngine._load_model(model_name)

        # Control whether embeddings get normalized before being returned.
        self.normalize_embeddings = normalize_embeddings

        logger.info(f"Embedding initialized with model: {model_name}")

    @staticmethod
    def _load_model(model_name: str) -> SentenceTransformer:
        """Load a SentenceTransformer model by name.

        Args:
            model_name (str): Name of the SentenceTransformer model to load.

        Returns:
            SentenceTransformer: Loaded model ready for inference.
        """
        return SentenceTransformer(model_name)

    def text_to_embedding(self, text: str) -> np.ndarray:
        """Generate an embedding vector for a single text input.

        Args:
            text (str): Input text to encode.

        Returns:
            numpy.ndarray: Embedding vector produced by the model.

        Raises:
            ValueError: If the provided text is empty or only whitespace.
        """
        if not text or not text.strip():
            raise ValueError("text_to_embedding received an empty text input.")

        embedding = self.model.encode(
            text, normalize_embeddings=self.normalize_embeddings, show_progress_bar=False
        )

        # Ensure a consistent numpy array output regardless of backend settings.
        return np.asarray(embedding, dtype=np.float32)


# Cache the engine so repeated calls reuse the same heavy model instance.


@lru_cache(maxsize=1)
def get_embedding(
    model_name: str = "all-MiniLM-L6-v2",
    normalize_embeddings: bool = True,
) -> EmbeddingEngine:
    """Return a cached EmbeddingEngine instance.

    Args:
        model_name (str): Name of the SentenceTransformer model to load.
        normalize_embeddings (bool): Flag indicating whether to normalize embeddings.

    Returns:
        EmbeddingEngine: Singleton-like instance cached via LRU.
    """
    return EmbeddingEngine(model_name, normalize_embeddings)


def get_embedding_instance() -> EmbeddingEngine:
    """Return the default embedding engine instance.

    Returns:
        EmbeddingEngine: Cached instance with default configuration.
    """
    return get_embedding()
