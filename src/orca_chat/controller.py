"""High-level orchestration of chat sessions."""

import logging
from collections.abc import AsyncIterator, Callable

from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.runnables.history import RunnableWithMessageHistory

from orca_chat.chains import build_chat_core, build_summarizer
from orca_chat.config import LLMConfig, LLMRegistry
from orca_chat.history import SessionState
from orca_chat.stages import ChatStage, StageTracker

log = logging.getLogger(__name__)

__all__ = ["ChatController"]


class ChatController:
    """Manage chat conversations and running summaries for multiple sessions."""

    def __init__(
        self,
        registry: LLMRegistry,
        *,
        default_alias: str | None = None,
        summarizer_alias: str | None = None,
        retrieval_factory: Callable[[str], BaseRetriever] | None = None,
        stage_tracker: StageTracker | None = None,
    ) -> None:
        """Create a new controller.

        Parameters
        ----------
        registry:
            Mapping of model aliases to :class:`LLMConfig` objects.
        default_alias:
            Alias of the chat model to use for regular conversations.
        summarizer_alias:
            Alias of the model used for history summarization.
        retrieval_factory:
            Optional callback returning a :class:`BaseRetriever` for an alias.
        stage_tracker:
            Custom :class:`StageTracker` for monitoring stage transitions.
        """
        self._registry = registry
        self._default_alias = default_alias or next(iter(registry))
        self._summarizer_alias = summarizer_alias or self._default_alias

        self._states: dict[str, SessionState] = {}
        self._chains: dict[tuple[str, str], RunnableWithMessageHistory] = {}

        self._retrieval_factory = retrieval_factory
        self._summarizers: dict[str, Runnable] = {}
        self._stage_tracker = stage_tracker or StageTracker()

    async def ainvoke_reply(
        self,
        session_id: str,
        message: str,
        *,
        alias: str | None = None,
    ) -> str:
        """Return the model's reply as a single string."""
        self._stage_tracker.set(session_id, ChatStage.SENDING_TO_MODEL)
        alias = alias or self._default_alias
        log_message = message.replace("\n", " ")
        log.info(
            "Invoking model: [%s, %s] %s (%d chars)",
            session_id,
            alias,
            log_message[:100] + "..." if len(message) > 100 else log_message,
            len(message),
        )
        chain = self._get_chain(session_id, self._default_alias)
        cfg: RunnableConfig = {"configurable": {"session_id": session_id}}

        self._stage_tracker.set(session_id, ChatStage.STREAM_FROM_CHAT)
        result = await chain.ainvoke({"input": message}, config=cfg)
        log_result = result.replace("\n", " ")
        log.info(
            "Received reply: [%s, %s] %s (%d chars)",
            session_id,
            alias,
            log_result[:100] + "..." if len(result) > 100 else log_result,
            len(result),
        )

        self._stage_tracker.set(session_id, ChatStage.SUMMARIZING_CHAT)
        await self._refresh_summary(session_id, self._summarizer_alias)

        self._stage_tracker.set(session_id, ChatStage.WAITING_FOR_USER)
        return str(result).strip()

    async def astream_reply(
        self,
        session_id: str,
        message: str,
        *,
        alias: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield the reply token by token as it is generated."""
        self._stage_tracker.set(session_id, ChatStage.SENDING_TO_MODEL)
        alias = alias or self._default_alias
        log_message = message.replace("\n", " ")
        log.info(
            "Streaming from model: [%s, %s] %s (%d chars)",
            session_id,
            alias,
            log_message[:100] + "..." if len(message) > 100 else log_message,
            len(message),
        )
        chain = self._get_chain(session_id, self._default_alias)
        cfg: RunnableConfig = {"configurable": {"session_id": session_id}}

        self._stage_tracker.set(session_id, ChatStage.STREAM_FROM_CHAT)
        result = ""
        async for token in chain.astream({"input": message}, config=cfg):
            result += token
            yield str(token)
        yield "\n"
        log_result = result.replace("\n", " ")
        log.info(
            "Received reply: [%s, %s] %s (%d chars)",
            session_id,
            alias,
            log_result[:100] + "..." if len(result) > 100 else log_result,
            len(result),
        )

        self._stage_tracker.set(session_id, ChatStage.SUMMARIZING_CHAT)
        await self._refresh_summary(session_id, self._summarizer_alias)

        self._stage_tracker.set(session_id, ChatStage.WAITING_FOR_USER)
        return

    def stage(self, session_id: str) -> ChatStage:
        """Return the current :class:`ChatStage` for ``session_id``."""
        return self._stage_tracker.get(session_id)

    def _state(self, session_id: str) -> SessionState:
        """Lazy-initialize and return ``SessionState`` for ``session_id``."""
        return self._states.setdefault(session_id, SessionState())

    def _ensure_summarizer(self, alias: str) -> None:
        """Instantiate the summarizer chain for ``alias`` if needed."""
        if alias not in self._summarizers:
            cfg: LLMConfig = self._registry[alias]
            self._summarizers[alias] = build_summarizer(cfg)

    def _get_chain(self, session_id: str, alias: str):
        """Return the chat chain for ``session_id`` and ``alias``."""
        key = (session_id, alias)
        if key in self._chains:
            return self._chains[key]

        state = self._state(session_id)
        cfg: LLMConfig = self._registry[alias]
        retriever = self._retrieval_factory(alias) if self._retrieval_factory else None
        core = build_chat_core(cfg, state.summary, retriever)

        chain = RunnableWithMessageHistory(
            core,
            lambda _: state.history,
            input_messages_key="input",
            history_messages_key="history",
        )
        self._chains[key] = chain
        return chain

    async def _refresh_summary(self, session_id: str, alias: str) -> None:
        """Regenerate the running summary for ``session_id``."""
        self._ensure_summarizer(alias)
        summarizer = self._summarizers[alias]

        state = self._state(session_id)
        new_summary = await summarizer.ainvoke({"history": state.history.messages})
        state.summary = str(new_summary).strip()
        log_result = state.summary.replace("\n", " ")
        log.info(
            "Updated summary: [%s, %s] %s (%d chars)",
            session_id,
            alias,
            log_result[:100] + "..." if len(state.summary) > 100 else log_result,
            len(state.summary),
        )
