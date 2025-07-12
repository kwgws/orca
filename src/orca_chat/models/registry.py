from langchain_ollama import ChatOllama

from .load import load_models

_DEFAULT_ALIAS = "default"


class LLMRegistry:
    """Cache and instantiate ``ChatOllama`` models by alias."""

    def __init__(self) -> None:
        """Return new :class:`LLMRegistry`."""
        self._cfg = load_models()
        self._models: dict[str, ChatOllama] = {}

    def get(self, name="default") -> ChatOllama:
        """Return cached model for _name_, or instantiate from its config."""
        alias = name if name in self._cfg else _DEFAULT_ALIAS
        if alias not in self._cfg:
            raise KeyError(f"Unknown model alias {name!r}; [default] not provided.")
        if alias not in self._models:
            self._models[alias] = self._instantiate(alias)
        return self._models[alias]

    def get_active(self) -> list[str]:
        """Return all known model aliases."""
        return list(self._cfg.keys())

    def register(self, name: str, instance: ChatOllama) -> None:
        """Register an initialized model instance."""
        self._models[name] = instance

    def refresh(self, name: str) -> ChatOllama:
        """Re-instantiate ``name`` from config and cache it."""
        if name in self._models:
            del self._models[name]
        return self.get(name)

    def _instantiate(self, alias: str) -> ChatOllama:
        """Instantiate the model configured for ``alias``."""
        # Allow ``model`` key to override alias.
        try:
            params = dict(self._cfg[alias])
        except KeyError as e:
            raise KeyError(f"Unknown model alias: {alias!r}") from e

        name = params.pop("model", alias)
        return ChatOllama(model=name, **params)  # type: ignore[arg-type]

    def __contains__(self, item: str) -> bool:
        return item in self._cfg

    def __iter__(self):
        return iter(self._cfg)

    def __len__(self) -> int:
        return len(self._cfg)
