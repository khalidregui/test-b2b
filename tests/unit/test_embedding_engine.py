from typing import Generator
from unittest.mock import MagicMock, call

import numpy as np
import pytest
from pytest_mock import MockerFixture

from backend.services.scrapping.embedding.embedding_engine import EmbeddingEngine, get_embedding


@pytest.fixture(autouse=True)
def reset_embedding_cache() -> Generator[None, None, None]:
    """Ensure the embedding cache is cleared between tests."""
    # Pre-test cleanup guarantees no state leakage from other test cases.
    get_embedding.cache_clear()
    yield
    # Post-test cleanup keeps the global cache pristine for subsequent tests.
    get_embedding.cache_clear()


def test_text_to_embedding_preserves_dtype_and_normalization(mocker: MockerFixture) -> None:
    """Ensure embeddings maintain float32 dtype and honor normalization settings.

    Args:
        mocker: Pytest fixture that simplifies dependency patching.
    """
    # Replace the heavy SentenceTransformer load with a deterministic stub.
    mock_model = MagicMock()
    mock_model.encode.return_value = np.array([0.11, 0.22, 0.33], dtype=np.float64)
    mocker.patch(
        "backend.services.scrapping.embedding.embedding_engine.EmbeddingEngine._load_model",
        return_value=mock_model,
    )

    # Instantiate the engine with normalization disabled to validate the flag propagation.
    engine = EmbeddingEngine(model_name="all-MiniLM-L6-v2", normalize_embeddings=False)

    # Convert a realistic telco meeting note into an embedding vector.
    embedding = engine.text_to_embedding("Discuss SLA upgrade with enterprise client")

    # Validate dtype coercion and confirm encode received the correct arguments.
    assert embedding.dtype == np.float32
    np.testing.assert_allclose(embedding, np.array([0.11, 0.22, 0.33], dtype=np.float32))
    mock_model.encode.assert_called_once_with(
        "Discuss SLA upgrade with enterprise client",
        normalize_embeddings=False,
        show_progress_bar=False,
    )


def test_get_embedding_caches_by_configuration(mocker: MockerFixture) -> None:
    """Verify cached instances reuse models only when configuration matches.

    Args:
        mocker: Pytest fixture that simplifies dependency patching.
    """
    # Provide distinct mock models so we can spot fresh loads versus cache hits.
    mock_models = [MagicMock(name=f"model_{idx}") for idx in range(2)]
    mocked_loader = mocker.patch(
        "backend.services.scrapping.embedding.embedding_engine.EmbeddingEngine._load_model",
        side_effect=mock_models,
    )

    # Prime the cache using the default configuration to simulate production reuse.
    first_engine = get_embedding()
    second_engine = get_embedding()

    # Inject a new configuration to trigger a fresh model load.
    third_engine = get_embedding(model_name="domain-specialized", normalize_embeddings=False)

    # Confirm only two loads occurred and cached instances are reused appropriately.
    assert first_engine is second_engine
    assert first_engine is not third_engine
    mocked_loader.assert_has_calls(
        [
            call("all-MiniLM-L6-v2"),
            call("domain-specialized"),
        ]
    )
    assert mocked_loader.call_count == 2


def test_text_to_embedding_rejects_blank_inputs(mocker: MockerFixture) -> None:
    """Ensure the engine refuses to embed empty strings, catching pipeline issues early.

    Args:
        mocker: Pytest fixture that simplifies dependency patching.
    """
    # Guard against accidental empty prompts by bypassing real model loading.
    mocker.patch(
        "backend.services.scrapping.embedding.embedding_engine.EmbeddingEngine._load_model",
        return_value=MagicMock(),
    )

    # Create the engine instance that will be shared across ingestion jobs.
    engine = EmbeddingEngine()

    # Validate that whitespace-only content raises a clear error instead of silent misuse.
    with pytest.raises(ValueError):
        engine.text_to_embedding("   ")
