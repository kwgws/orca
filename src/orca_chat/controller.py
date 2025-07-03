"""
Chat session controller for orchestrating LLM-based conversations.

This module defines the `ChatController` class, which manages multi-session
chat interactions using large language models (LLMs). It handles stateful
message history, chat stage transitions, streaming or non-streaming model
responses, and the generation of running précis (summaries) per session.
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable

from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.runnables.history import RunnableWithMessageHistory

from orca_chat.chains import build_editor_llm, build_llm
from orca_chat.config import LLMConfig, LLMRegistry
from orca_chat.state import ChatStage, SessionState, StageTracker

log = logging.getLogger(__name__)


class ChatController:
    """Manage chat conversations and running précis for multiple sessions.

    This class coordinates interactions with multiple language models,
    maintains per-session state and history, handles chat stages, and
    generates summaries of each session.
    """

    def __init__(
        self,
        registry: LLMRegistry,
        alias: str | None = None,
        *,
        editor_alias: str | None = None,
        retriever_factory: Callable[[str], BaseRetriever] | None = None,
        stage_tracker: StageTracker | None = None,
    ) -> None:
        """Create a new :class:`ChatController`.

        Parameters
        ----------
        registry:
            Mapping of model aliases to :class:`LLMConfig` objects.
        alias:
            Alias of the chat model to use for regular conversations.
        editor_alias:
            Alias of the model used for writing précis.
        retriever_factory:
            Optional callback returning a :class:`BaseRetriever` for an alias.
        stage_tracker:
            Custom :class:`StageTracker` for monitoring stage transitions.
        """
        self._registry = registry
        self._alias = alias or next(iter(registry))
        self._editor_alias = editor_alias or self._alias

        self._states: dict[str, SessionState] = {}
        self._chains: dict[tuple[str, str], RunnableWithMessageHistory] = {}
        self._chain_precis: dict[tuple[str, str], str] = {}
        self._editors: dict[str, Runnable] = {}
        self._retriever_factory = retriever_factory
        self._stage_tracker = stage_tracker or StageTracker()

    def get_stage(self, session_id: str) -> ChatStage:
        """Return the current :class:`ChatStage` for the ``session_id``."""
        return self._stage_tracker.get(session_id)

    async def ainvoke_reply(
        self,
        session_id: str,
        message: str,
        *,
        alias: str | None = None,
    ):
        """Send a message to the model and return the generated reply.

        Parameters
        ----------
        session_id : str
            The identifier for the chat session.
        message : str
            The user message to send.
        alias : str, optional
            Alias of the model to use, if not the controller default.

        Returns
        ------
        str
            The model's reply.
        """
        return await self._get_reply(session_id, message, alias=alias)

    async def astream_reply(
        self,
        session_id: str,
        message: str,
        *,
        alias: str | None = None,
    ) -> AsyncIterator[str]:
        """Send a message to the model and stream the reply token-by-token.

        Parameters
        ----------
        session_id : str
            The identifier for the chat session.
        message : str
            The user message to send.
        alias : str, optional
            Alias of the model to use, if not the controller default.

        Yields
        ------
        str
            The next token in the model's reply.
        """
        queue: asyncio.Queue[str] = asyncio.Queue()

        async def _push(token: str) -> None:
            await queue.put(token)

        task = asyncio.create_task(
            self._get_reply(session_id, message, alias=alias, on_token=_push)
        )

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
        state = self._state(session_id)

        precis = state.precis
        key = (session_id, alias)
        if key in self._chains and self._chain_precis.get(key) == precis:
            return self._chains[key]

        cfg: LLMConfig = self._registry[alias]
        retriever = self._retriever_factory(alias) if self._retriever_factory else None
        chain = RunnableWithMessageHistory(
            build_llm(cfg, precis, retriever),
            lambda _: state.history,
            input_messages_key="input",
            history_messages_key="history",
        )

        self._chains[key] = chain
        self._chain_precis[key] = precis
        return chain

    async def _get_reply(
        self,
        session_id: str,
        message: str,
        *,
        alias: str | None = None,
        editor_alias: str | None = None,
        on_token: Callable[[str], Awaitable[None]] | None = None,
    ):
        """Send message to the model, get response, and update précis."""
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

    def _get_editor(self, editor_alias: str) -> Runnable:
        """Instantiate the editor chain for ``editor_alias`` if needed."""
        if editor_alias not in self._editors:
            cfg: LLMConfig = self._registry[editor_alias]
            self._editors[editor_alias] = build_editor_llm(cfg)
        return self._editors[editor_alias]

    async def _edit(self, session_id: str, alias: str) -> None:
        """Regenerate the running precis for ``session_id``."""
        state = self._state(session_id)
        editor = self._get_editor(alias)

        # TODO: Occasionally this returns a blank précis--we need to make sure
        #       that doesn't happen before we replace the old one!
        edit = await editor.ainvoke({"history": state.history.messages})
        new_precis = str(edit).strip()
        if not new_precis:
            log.warning(
                "Editor produced empty précis: [%s, %s], keeping previous value", session_id, alias
            )
            return

        state.precis = str(new_precis).strip()

        log_result = state.precis.replace("\n", " ")
        log.info(
            "Summarized [%s, %s]: %s (%d chars)",
            session_id,
            alias,
            log_result[:100] + "..." if len(state.precis) > 100 else log_result,
            len(state.precis),
        )
