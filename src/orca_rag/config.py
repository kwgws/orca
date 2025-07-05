"""Configuration utilities; uses environment variables.

This module centralises all environment-driven configuration in a set of
immutable dataclasses. Import modules can obtain a singleton instance via
`get_settings()` and trust that the values stay consistent.
"""

import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Any

__all__ = ["ChromaConfig", "ModelConfig", "Settings", "get_settings"]


def _env_s(key: str, default="") -> str:
    """Return string value from `os.environ[key]`."""
    return os.getenv(key, default)


def _env_n(key: str, default=0) -> int:
    """Return integer value from `os.environ[key]`."""
    return int(os.getenv(key, str(default)))


def _env_f(key: str, default=0.0) -> float:
    """Return float value from `os.environ[key]`."""
    return float(os.getenv(key, str(default)))


def _env_b(key: str, default=False) -> bool:
    """Return boolean value from `os.environ[key]`.

    Returns `True` on `"1"`, `"true"`, or `"yes"`.
    """
    value = os.getenv(key)
    return default if value is None else value.lower() in {"1", "true", "yes"}


def _check_range(name: str, value: float, lo: float, hi: float | None = None) -> None:
    """Raise if `value` ∉ [`lo`, `hi`]."""
    if hi is None:
        if not lo <= value:
            raise ValueError(f"{name}={value!r} must be >= {lo}")
    elif not lo <= value <= hi:
        raise ValueError(f"{name}={value!r} must be in the range [{lo}, {hi}]")


@dataclass(frozen=True, slots=True)
class ModelConfig:
    """Injectable spec for a single large language model.

    Attributes
    ----------
    model : str
        Model identifier (e.g. "llama3").
    base_url : str
        Endpoint of the inference server. Defaults to local Ollama instance.
    temperature : float, optional
        Softmax temperature τ. Lower -> more deterministic; higher -> more
        creative. Typical range 0.2 - 1.2.
    top_k : int, optional
        Top-K sampling. Keep only the *k* most-likely tokens, renormalize
        probabilities to 1.0, then sample. Typical range 20 - 100.
    top_p : float, optional
        Nucleus (Top-P) sampling. Select the smallest set of tokens whose
        cumulative probability >= p, then sample from that set. Typical
        values 0.8 - 0.95.
    repetition_penalty : float, optional
        Multiply logits of already-generated tokens by this factor (< 1
        discourages loops, > 1 encourages repetition). Common: 0.9 - 1.1.
    extra_params : Mapping[str, Any], optional
        Provider-specific kwargs passed straight through to the backend.
    """

    model: str
    base_url: str = "http://localhost:11434"
    temperature: float | None = None
    top_k: int | None = None
    top_p: float | None = None
    repetition_penalty: float | None = None
    extra_params: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.temperature is not None:
            _check_range("temperature", self.temperature, 0.0, 2.0)
        if self.top_k is not None and self.top_p is not None:
            raise ValueError("LLM configuration error: top_k and top_p cannot be used together")
        if self.top_k is not None:
            if not isinstance(self.top_k, int) or self.top_k < 1:
                raise ValueError("LLM configuration error: top_k must be an integer >= 1")
        if self.top_p is not None:
            _check_range("top_p", self.top_p, 0.0, 1.0)
        if self.repetition_penalty is not None:
            _check_range("repetition_penalty", self.repetition_penalty, 0.5)

    def to_request_dict(self) -> dict[str, Any]:
        """Return serializable dictionary for Ollama's `/api/generate`."""
        data = {k: v for k, v in asdict(self).items() if v is not None}
        data.pop("base_url")

        # Don't let extra_params overwrite explicit fields.
        extra_params = data.pop("extra_params")
        data.update({k: v for k, v in extra_params.items() if k not in data})

        return data


@dataclass(frozen=True, slots=True)
class ChromaConfig:
    """Connection and retrieval parameters for a Chroma vector store.

    Attributes
    ----------
    collection : str
        Name of the Chroma collection to query.
    k : int
        Number of documents to fetch per query, pre-rerank. Defaults to 15.
    url : str
        Base URL of the Chroma HTTP server. Defaults to localhost.
    embed_model : ModelConfig
        Model used to generate embeddings when ingesting or querying vectors.
        Defaults to nomic-embed-text running on a local Ollama instance.
    database : str, optional
        Logical database (namespace) inside Chroma.
    tenant : str, optional
        Tenant identifier for multi-tenant deployments.
    """

    collection: str = "default"
    k: int = 15
    url: str = "http://localhost:8000"
    embed_model: ModelConfig = field(
        default_factory=lambda: ModelConfig(
            model=_env_s("CHROMA_EMBED_MODEL", "nomic-embed-text"),
            base_url=_env_s("CHROMA_EMBED_URL", "http://localhost:11434"),
        )
    )
    database: str = "default_database"
    tenant: str = "default_tenant"

    def __post_init__(self) -> None:
        _check_range("chroma k", self.k, 1)


@dataclass(frozen=True, slots=True)
class Settings:
    """Top-level application settings bundle.

    The class is immutable and should be accessed via :func:`get_settings` so
    that the same instance is shared across the entire process.

    Attributes
    ----------
    chat_model : ModelConfig
        Language model configuration for use with chat functions.
    chroma : ChromaConfig
        Chroma configuration for use with RAG operations.
    """

    chat_model: ModelConfig = field(
        default_factory=lambda: ModelConfig(
            model=_env_s("CHAT_MODEL", "llama3"),
            temperature=_env_f("CHAT_TEMPERATURE") or None,
            top_k=_env_n("CHAT_TOP_K") or None,
            top_p=_env_f("CHAT_TOP_P") or None,
            repetition_penalty=_env_f("CHAT_REPETITION_PENALTY") or None,
            base_url=_env_s("CHAT_URL", "http://localhost:11434"),
        )
    )
    chroma: ChromaConfig = field(
        default_factory=lambda: ChromaConfig(
            collection=_env_s("CHROMA_COLLECTION", "default"),
            k=_env_n("CHROMA_K", 15),
            url=_env_s("CHROMA_URL", "http://localhost:8000"),
        )
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    The first call instantiates the dataclass; subsequent calls return the same
    object, ensuring that configuration is read exactly once per process.
    """
    return Settings()
