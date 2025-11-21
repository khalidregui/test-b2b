from functools import lru_cache

import dataiku
import numpy as np
from dataikuapi.dss.llm import DSSLLM
from loguru import logger


class DataikuEmbeddingEngine:
    """Embedding utilities backed by Dataiku's LLM service.

    This engine uses Dataiku DSS's LLM interface to request text
    embeddings from a configured provider (e.g., Vertex AI, OpenAI)
    identified by a Dataiku model identifier.

    Attributes:
        model_id (str): Dataiku LLM identifier for the embedding endpoint.
        model (DSSLLM): Dataiku DSS LLM client bound to `model_id`.
    """

    def __init__(
        self, model_id: str = "openai:artefact-llm-proxy:vertex_ai/text-multilingual-embedding-002"
    ) -> None:
        self.model_id = model_id
        self.model = DataikuEmbeddingEngine._load_model(self.model_id)

        logger.info(f"Embedding initialized with model: {self.model_id}")

    @staticmethod
    def _load_model(model_id: str) -> DSSLLM:
        """Resolve a Dataiku LLM embedding client by identifier.

        Args:
            model_id (str): Dataiku LLM identifier, such as
                "openai:artefact-llm-proxy:vertex_ai/text-multilingual-embedding-002".

        Returns:
            DSSLLM: A handle to the configured embedding endpoint ready for inference.
        """
        client = dataiku.api_client()
        project = client.get_default_project()

        return project.get_llm(model_id)

    def text_to_embedding(self, text: str) -> np.ndarray:
        """Generate a single-vector embedding for a text input via Dataiku.

        Args:
            text (str): Input text to embed.

        Returns:
            numpy.ndarray: 1D embedding vector returned by the Dataiku LLM endpoint.

        Raises:
            ValueError: If `text` is empty or only whitespace.
        """
        if not text or not text.strip():
            raise ValueError("text_to_embedding received an empty text input.")

        emb_query = self.model.new_embeddings()
        emb_query.add_text(text)
        emb_resp = emb_query.execute()
        embedding = emb_resp.get_embeddings()[0]

        # Cast to a NumPy array to ensure a consistent, typed vector output.
        return np.asarray(embedding, dtype=np.float32)


# Cache the engine so repeated calls reuse the same Dataiku client handle.


@lru_cache(maxsize=1)
def get_embedding(
    model_id: str = "openai:artefact-llm-proxy:vertex_ai/text-multilingual-embedding-002",
) -> DataikuEmbeddingEngine:
    """Return a cached DataikuEmbeddingEngine instance.

    Args:
        model_id (str): Dataiku LLM identifier of the embedding endpoint.

    Returns:
        DataikuEmbeddingEngine: Singleton-like instance cached via LRU.
    """
    return DataikuEmbeddingEngine(model_id)


def get_embedding_instance() -> DataikuEmbeddingEngine:
    """Return the default Dataiku embedding engine instance.

    Returns:
        DataikuEmbeddingEngine: Cached instance with the default model configuration.
    """
    return get_embedding()
