"""orca_chat.core.skills
Base abstractions for skills.

A skill is the smallest unit of work that can mutate a :class:`Session`
(answer a question, summarize a chat, call an external API, etc).
"""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, Final

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

from .llm import LLMStore
from .node import Node, NodeStore
from .session import Session

__all__: Final = ["LLMSkillMixin", "Skill", "register_skill", "register_skills"]


@dataclass(slots=True, frozen=True)
class Skill(ABC):
    """Abstract base class for skills.

    Attributes
    ----------
    name
        Globally-unique, human-readable identifier.
    tags
        Immutable set of strings used for tracing & by callbacks.
    __call__
        Async factory to be called by the state graph.
    """

    name: ClassVar[str]
    tags: ClassVar[frozenset[str]]

    @abstractmethod
    async def __call__(self, state: Session, config: RunnableConfig) -> Session: ...


@dataclass(slots=True, frozen=True)
class LLMSkillMixin(ABC):
    """Helper mixin for LLM-driven skills.

    Attributes
    ----------
    llm:
        A concrete, callback-ready :class:`BaseChatModel`, to be injected by
        :func:`register_skill`.
    llm_alias:
        Symbolic name used when fetching the model from :class:`LLMStore`.
    """

    llm: BaseChatModel
    llm_alias: ClassVar[str]

    async def _run_llm(self, prompt: Sequence, config: RunnableConfig) -> str:
        """Stream `prompt` through :pyattr:`llm` and return the full text.

        The method merges the caller's :class:`RunnableConfig` with our tags,
        injects callbacks (if any), and concatenates streamed chunks from the
        model into a single, stripped string.
        """
        cfg: RunnableConfig = {
            **config,
            "tags": [*config.get("tags", []), *getattr(self, "tags", [])],
        }
        runnable = (
            self.llm.with_config(callbacks=cfg.pop("callbacks", None))
            if "callbacks" in cfg
            else self.llm
        )
        chunks: list[str] = []
        async for chunk in runnable.astream(prompt, config=cfg):
            chunks.append(str(chunk.content) or "")
        return "".join(chunks).strip()


async def register_skill(
    skill: type[Skill], node_store: NodeStore, llm_store: LLMStore
) -> Node[Session]:
    """Instantiate skill, wire its factory, and register a node.

    Parameters
    ----------
    skill:
        The class object (NOT INSTANCE) of the skill to register.
    node_store:
        Graph-wide registry that owns :class:`Node` instances.
    llm_store:
        Global :class:`LLMStore` used to resolve LLMs.

    Returns
    -------
    Node
        The registered node, ready to be composed into the graph.
    """

    # Is it a LLM-backed skill?
    if issubclass(skill, LLMSkillMixin):
        llm = await llm_store.get(skill.llm_alias)

        async def _factory(state: Session, config: RunnableConfig) -> Session:
            return await skill(llm)(state, config)  # type: ignore[arg-type]

        return await node_store.register(
            name=skill.name,
            tags=set(skill.tags),
            factory=_factory,
            metadata={"llm_alias": skill.llm_alias},
        )

    # ...or is it plain Python?
    async def _factory(state: Session, config: RunnableConfig) -> Session:
        return await skill()(state, config)

    return await node_store.register(
        name=skill.name,
        tags=set(skill.tags),
        factory=_factory,
    )


async def register_skills(
    *skills: type[Skill], node_store: NodeStore, llm_store: LLMStore
) -> list[Node[Session]]:
    """Convenience wrapper for registering multiple skills at once."""
    return list(
        await asyncio.gather(
            *(register_skill(skill, node_store, llm_store) for skill in skills),
        )
    )
