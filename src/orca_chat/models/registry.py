from langchain_ollama import ChatOllama

from .load import load_models

_DEFAULT_ALIAS = "default"


class LLMRegistry:
    """Registry for language model instances.

    Parameters
    ----------
    cfg :
        Mapping of model-alias -> kwargs passed to underlying model.
    model_cls :
        Concrete model class returned by :meth:`get`.
    """

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
        """Return all registered model aliases."""
        return list(self._cfg.keys())

    def register(self, name: str, instance: ChatOllama) -> None:
        """Register pre-instantiated model at alias _name_."""
        self._models[name] = instance

    def refresh(self, name: str) -> ChatOllama:
        """Re-instantiate _name_ from its config, replacing cached copy."""
        if name in self._models:
            del self._models[name]
        return self.get(name)

    def _instantiate(self, alias: str) -> ChatOllama:
        """Register new model instance for _alias_.

        If a _model_ key is provided in `_self.cfg` we treat that as the actual
        model name, otherwise we use _alias_.
        """
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
