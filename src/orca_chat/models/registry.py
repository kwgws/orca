from collections.abc import Mapping

from langchain_ollama import ChatOllama

__all__ = ["LLMRegistry"]

MODEL_CLASSES: dict[str, type] = {
    "ollama": ChatOllama,
    # "openai": ChatOpenAI,
}


class LLMRegistry:
    def __init__(self, cfg: Mapping[str, Mapping[str, object]]):
        self._cfg: dict[str, Mapping[str, object]] = dict(cfg)
        self._models: dict[str, object] = {}

    @classmethod
    def from_dict(cls, cfg: Mapping[str, Mapping[str, object]]):
        return cls(cfg)

    def get(self, name: str):
        if name not in self._models:
            self._models[name] = self._instantiate(name)
        return self._models[name]

    def get_active(self):
        return list(self._cfg.keys())

    def register(self, name: str, instance: object):
        self._models[name] = instance

    def refresh(self, name: str):
        if name in self._models:
            del self._models[name]
        return self.get(name)

    def _instantiate(self, name: str):
        if name not in self._cfg:
            raise KeyError(f"Unknown model alias: {name!r}")

        params = dict(self._cfg[name])
        provider = str(params.pop("provider", "ollama"))

        try:
            model_cls = MODEL_CLASSES[provider]
        except KeyError as e:
            raise NotImplementedError(f"Unsupported provider: {provider!r}") from e

        return model_cls(model=name, **params)

    def __contains__(self, item: str):
        return item in self._cfg

    def __iter__(self):
        return iter(self._cfg)

    def __len__(self):
        return len(self._cfg)
