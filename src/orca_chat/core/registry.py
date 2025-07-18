"""orca_chat/core/registry.py"""

import asyncio
import importlib
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.runnables import Runnable
from langchain_ollama import ChatOllama
from langgraph.graph.state import CompiledStateGraph

from ..config.load import SKILLS_DIR, SkillConfig, load_skill

# Hashable dict key; model, base_url, params.
# If any of these change we need a new ChatOllama client.
LLMKey = tuple[str, str, frozenset[tuple[str, Any]]]

# Callable that, when invoked, yields a Runnable node.
NodeFactory = Callable[[], Runnable]


@dataclass(slots=True)
class LLMRegistry:
    """Lazily manages ChatOllama clients across the app.

    Parameters
    ----------
    config_dir : str or Path, optional
        Directory containing ``<skill>.toml``.
        Defaults to the config directory's ``skills`` folder.
    """

    config_dir: str | Path = SKILLS_DIR

    _config_cache: dict[str, SkillConfig] = field(init=False, default_factory=dict)
    _llm_cache: dict[LLMKey, ChatOllama] = field(init=False, default_factory=dict)
    _factory_cache: dict[str, NodeFactory] = field(init=False, default_factory=dict)
    _graph_cache: dict[str, CompiledStateGraph] = field(init=False, default_factory=dict)
    _locks: defaultdict[str, asyncio.Lock] = field(
        init=False, default_factory=lambda: defaultdict(lambda: asyncio.Lock())
    )
    _dir: Path = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_dir", Path(self.config_dir).resolve())

    async def get_config(self, name: str) -> SkillConfig:
        """Return parsed and validated :class:`SkillConfig`."""
        async with self._locks[name]:
            if name in self._config_cache:
                return self._config_cache[name]

            cfg: SkillConfig = await asyncio.to_thread(load_skill, name, self._dir)
            self._config_cache[name] = cfg
            return cfg

    async def get_llm(self, alias: str) -> ChatOllama:
        """Return cached :class:`ChatOllama` client for given ``alias``."""
        cfg = await self.get_config(alias)
        key: LLMKey = (cfg.model, cfg.base_url, frozenset(cfg.params.items()))

        async with self._locks[alias]:
            if key in self._llm_cache:
                return self._llm_cache[key]

            llm = await asyncio.to_thread(
                ChatOllama, model=cfg.model, base_url=cfg.base_url, **cfg.params
            )
            self._llm_cache[key] = llm
            return llm

    async def get_factory(self, name: str) -> NodeFactory:
        """Return a cached ``RunnableFactory`` for the given skill name."""
        async with self._locks[name]:
            if name in self._factory_cache:
                return self._factory_cache[name]

            cfg = await self.get_config(name)
            llm = await self.get_llm(name)

            mod_path = f"orca_chat.skills.{name}"
            try:
                mod = importlib.import_module(mod_path)
            except ModuleNotFoundError as e:
                raise ValueError(f"Module '{mod_path}' missing for skill '{name}'") from e

            builder = getattr(mod, "build", None)
            if builder is None:
                raise AttributeError(f"Module '{mod_path}' must expose a 'build()' function.")

            def factory(**kwargs: Any) -> Runnable:
                return builder(llm, cfg, **kwargs)

            self._factory_cache[name] = factory
            return factory

    async def get_graph(self, name: str) -> CompiledStateGraph:
        """Import graph and compile once."""
        async with self._locks[name]:
            if name in self._graph_cache:
                return self._graph_cache[name]

            mod_path = f"orca_chat.graphs.{name}"
            try:
                mod = importlib.import_module(mod_path)
            except ModuleNotFoundError as e:
                raise ValueError(f"Module '{mod_path}' missing for graph '{name}'") from e

            compiler = getattr(mod, "compile", None)
            if compiler is None:
                raise AttributeError(f"Module '{mod_path}' must expose a 'compile()' function.")

            graph: CompiledStateGraph = await compiler(self)
            self._graph_cache[name] = graph
            return graph
