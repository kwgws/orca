"""orca_chat/skills/base.py"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Final

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

from .llm import LLMStore
from .node import Node, NodeStore
from .session import Session

__all__: Final = ["LLMSkillMixin", "Skill", "register_skill"]


@dataclass(slots=True, frozen=True)
class Skill(ABC):
    name: ClassVar[str]
    tags: ClassVar[frozenset[str]]

    @abstractmethod
    async def __call__(self, state: Session, config: RunnableConfig) -> Session: ...


@dataclass(slots=True, frozen=True)
class LLMSkillMixin(ABC):
    llm: BaseChatModel
    llm_alias: ClassVar[str]


async def register_skill(
    skill_cls: type[Skill], node_store: NodeStore, llm_store: LLMStore
) -> Node:
    """Register a skill in the node store"""
    if issubclass(skill_cls, LLMSkillMixin):
        llm = llm_store.get(skill_cls.llm_alias)

        async def factory(state: Session, config: RunnableConfig) -> Session:
            return await skill_cls(llm)(state, config)  # type: ignore

        return await node_store.register(
            name=skill_cls.name,
            factory=factory,
            tags=set(skill_cls.tags),
            metadata={"llm_alias": skill_cls.llm_alias},
        )

    async def factory(state: Session, config: RunnableConfig) -> Session:
        return await skill_cls()(state, config)

    return await node_store.register(
        name=skill_cls.name,
        factory=factory,
        tags=set(skill_cls.tags),
    )
