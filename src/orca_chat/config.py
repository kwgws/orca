"""LLM configuration primitives.

This module keeps all the twistable knobs for our language models in one place,
so higher level code can swap or fine tune models without rummaging through
business logic or UI layers.
"""

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = ["LLMConfig", "LLMRegistry"]


def _range_check(name: str, value: float, lo: float, hi: float) -> None:
    """Raise if `value` ∉ [`lo`, `hi`]."""
    if not lo <= value <= hi:
        raise ValueError(f"{name}={value!r} must be in the range [{lo}, {hi}].")


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """Injectable spec for a single chat-completion model.

    Fields
    ----------
    model: str
        Model identifier (e.g. ``"llama3"``).

    temperature: float, optional
        **Softmax temperature τ.** Lower → more deterministic (0 ≈ greedy);
        higher → more creative. Typical range 0.2 - 1.2.

    top_k: int, optional
        **Top-K sampling.** Keep only the *k* most-likely tokens, renormalize
        probabilities to 1.0, then sample. Typical range 20 - 100.

    top_p: float, optional
        **Nucleus (Top-P) sampling.** Select the smallest set of tokens whose
        cumulative probability ≥ *p*, then sample from that set.
        Typical values 0.8 - 0.95.

    repetition_penalty: float, optional
        Multiply logits of already-generated tokens by this factor (< 1
        discourages loops, > 1 encourages repetition). Common: 0.9 - 1.1.

    system: str, optional
        System-level message prepended to every conversation.

    stop: Sequence[str], optional
        Token(s) at which generation should halt cleanly.

    base_url: str, default ``"http://localhost:11434"``
        Endpoint of the inference server.

    timeout_s: int, default ``60``
        HTTP timeout (seconds) for a single completion request.

    extra_params: Mapping[str, Any], optional
        Provider-specific kwargs passed straight through to the backend.
    """

    model: str
    temperature: float | None = None
    top_k: int | None = None
    top_p: float | None = None
    repetition_penalty: float | None = None
    system: str = ""
    stop: Sequence[str] = field(default_factory=list)
    base_url: str = "http://localhost:11434"
    timeout_s: int = 60
    extra_params: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.temperature is not None:
            _range_check("temperature", self.temperature, 0.0, 2.0)

        if self.top_k is not None and self.top_p is not None:
            raise ValueError("top_k and top_p cannot be used together.")

        if self.top_k is not None:
            if not isinstance(self.top_k, int) or self.top_k < 1:
                raise ValueError("top_k must be an integer ≥ 1.")

        if self.top_p is not None:
            _range_check("top_p", self.top_p, 0.0, 1.0)

        if self.repetition_penalty is not None:
            _range_check("repetition_penalty", self.repetition_penalty, 0.5, 1.5)

        bad = [tok for tok in self.stop if not isinstance(tok, str) or tok == ""]
        if bad:
            raise TypeError(f"Stop tokens must be non-empty strings: {bad!r}")

    def to_request_dict(self) -> dict[str, Any]:
        """Return a dict ready for `ollama.Chat()`. Drops `None` values."""
        data = {
            "model": self.model,
            "temperature": self.temperature,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "repetition_penalty": self.repetition_penalty,
            "system": self.system,
            "stop": list(self.stop) or None,
        }
        data.update(self.extra_params)
        return {key: value for key, value in data.items() if value is not None}


class LLMRegistry(MutableMapping[str, LLMConfig]):
    """Dict-like mapping from `name` → `LLMConfig`.

    Having a dedicated registry means the application*layer can ask for
    "chat" or "memo" models without hard-coding endpoints. Swap entries at
    runtime for A/B tests or per-user preferences.
    """

    def __init__(self, *cfgs: LLMConfig):
        self._store: dict[str, LLMConfig] = {cfg.model: cfg for cfg in cfgs}

    def __getitem__(self, key: str) -> LLMConfig:
        return self._store[key]

    def __setitem__(self, key: str, value: LLMConfig) -> None:
        self._store[key] = value

    def __delitem__(self, key: str) -> None:
        del self._store[key]

    def __iter__(self):
        return iter(self._store)

    def __len__(self) -> int:
        return len(self._store)

    def add(self, cfg: LLMConfig, alias: str | None) -> None:
        self._store[alias or cfg.model] = cfg
