"""High-level orchestration of chat sessions."""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable

from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.runnables.history import RunnableWithMessageHistory

from orca_chat.chains import build_editor_llm, build_llm
from orca_chat.config import LLMConfig, LLMRegistry
from orca_chat.history import SessionState
from orca_chat.stages import ChatStage, StageTracker

log = logging.getLogger(__name__)


class ChatController:
    """Manage chat conversations and running précis for multiple sessions."""

    def __init__(
        self,
        registry: LLMRegistry,
        alias: str | None = None,
        *,
        editor_alias: str | None = None,
        retrieval_factory: Callable[[str], BaseRetriever] | None = None,
        stage_tracker: StageTracker | None = None,
    ) -> None:
        """Create a new controller.

        Parameters
        ----------
        registry:
            Mapping of model aliases to :class:`LLMConfig` objects.
        alias:
            Alias of the chat model to use for regular conversations.
        editor_alias:
            Alias of the model used for writing prècis.
        retrieval_factory:
            Optional callback returning a :class:`BaseRetriever` for an alias.
        stage_tracker:
            Custom :class:`StageTracker` for monitoring stage transitions.
        """
        self._registry = registry
        self._alias = alias or next(iter(registry))
        self._editor_alias = editor_alias or self._alias

        self._states: dict[str, SessionState] = {}
        self._chains: dict[tuple[str, str], RunnableWithMessageHistory] = {}
        self._editors: dict[str, Runnable] = {}
        self._retrieval_factory = retrieval_factory
        self._stage_tracker = stage_tracker or StageTracker()

    def get_stage(self, session_id: str) -> ChatStage:
        """Return the current :class:`ChatStage` for ``session_id``."""
        return self._stage_tracker.get(session_id)

    async def ainvoke_reply(
        self,
        session_id: str,
        message: str,
        *,
        alias: str | None = None,
    ):
        return await self._run(session_id, message, alias=alias)

    async def astream_reply(
        self,
        session_id: str,
        message: str,
        *,
        alias: str | None = None,
    ) -> AsyncIterator[str]:
        queue: asyncio.Queue[str] = asyncio.Queue()

        async def _push(token: str) -> None:
            await queue.put(token)

        task = asyncio.create_task(self._run(session_id, message, alias=alias, on_token=_push))
        try:
            while True:
                token = await queue.get()
                yield token
                queue.task_done()
        finally:
            await task

    def _state(self, session_id: str) -> SessionState:
        """Lazy-initialize and return ``SessionState`` for ``session_id``."""
        return self._states.setdefault(session_id, SessionState())

    def _get_chain(self, session_id: str, alias: str):
        """Return the chat chain for ``session_id`` and ``alias``."""
        key = (session_id, alias)
        if key in self._chains:
            return self._chains[key]

        state = self._state(session_id)
        cfg: LLMConfig = self._registry[alias]
        retriever = self._retrieval_factory(alias) if self._retrieval_factory else None
        core = build_llm(cfg, state.precis, retriever)

        chain = RunnableWithMessageHistory(
            core,
            lambda _: state.history,
            input_messages_key="input",
            history_messages_key="history",
        )
        self._chains[key] = chain
        return chain

    async def _run(
        self,
        session_id: str,
        message: str,
        *,
        alias: str | None = None,
        editor_alias: str | None = None,
        on_token: Callable[[str], Awaitable[None]] | None = None,
    ):
        """Send message to the model, stream or return response, and update precis."""
        self._stage_tracker.set(session_id, ChatStage.STARTED_STREAM)
        alias = alias or self._alias
        chain = self._get_chain(session_id, alias)
        cfg: RunnableConfig = {"configurable": {"session_id": session_id}}
        reply = ""

        log_message = message.replace("\n", " ")
        log.info(
            "%s [%s, %s]: %s (%d chars)",
            "Streaming" if on_token else "Invoking",
            session_id,
            alias,
            log_message[:100] + "..." if len(message) > 100 else log_message,
            len(message),
        )

        try:
            if on_token is None:
                reply = await chain.ainvoke({"input": message}, config=cfg)
            else:
                async for chunk in chain.astream({"input": message}, config=cfg):
                    token = str(chunk)
                    reply += token
                    await on_token(token)
        except Exception as e:
            self._stage_tracker.set(session_id, ChatStage.AWAITING_INPUT)
            log.error("Model call failed [%s, %s]: %s", session_id, alias, e)
            raise

        log_reply = reply.replace("\n", " ")
        log.info(
            "Replied [%s, %s]: %s (%d chars)",
            session_id,
            alias,
            log_reply[:100] + "..." if len(reply) > 100 else log_reply,
            len(reply),
        )

        self._stage_tracker.set(session_id, ChatStage.STARTED_PRECIS)
        await self._edit(session_id, editor_alias or self._editor_alias)

        self._stage_tracker.set(session_id, ChatStage.AWAITING_INPUT)
        return reply.strip()

    def _get_editor(self, editor_alias: str) -> None:
        """Instantiate the editor chain for ``editor_alias`` if needed."""
        if editor_alias not in self._editors:
            cfg: LLMConfig = self._registry[editor_alias]
            self._editors[editor_alias] = build_editor_llm(cfg)

    async def _edit(self, session_id: str, alias: str) -> None:
        """Regenerate the running precis for ``session_id``."""
        self._get_editor(alias)
        editor = self._editors[alias]

        state = self._state(session_id)
        new_precis = await editor.ainvoke({"history": state.history.messages})
        state.precis = str(new_precis).strip()
        log_result = state.precis.replace("\n", " ")
        log.info(
            "Summarized [%s, %s]: %s (%d chars)",
            session_id,
            alias,
            log_result[:100] + "..." if len(state.precis) > 100 else log_result,
            len(state.precis),
        )
