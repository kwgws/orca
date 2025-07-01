from collections.abc import AsyncIterator, Callable

from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.runnables.history import RunnableWithMessageHistory

from orca_chat.chains import build_chat_core, build_summarizer
from orca_chat.config import LLMConfig, LLMRegistry
from orca_chat.history import SessionState
from orca_chat.stages import ChatStage, StageTracker

__all__ = ["ChatController"]


class ChatController:
    def __init__(
        self,
        registry: LLMRegistry,
        *,
        default_alias: str | None = None,
        summarizer_alias: str | None = None,
        retrieval_factory: Callable[[str], BaseRetriever] | None = None,
        stage_tracker: StageTracker | None = None,
    ) -> None:
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
    ) -> str:
        self._stage_tracker.set(session_id, ChatStage.SENDING_TO_MODEL)
        chain = self._get_chain(session_id, self._default_alias)
        cfg: RunnableConfig = {"configurable": {"session_id": session_id}}

        self._stage_tracker.set(session_id, ChatStage.STREAM_FROM_CHAT)
        result = await chain.ainvoke({"input": message}, config=cfg)

        self._stage_tracker.set(session_id, ChatStage.SUMMARIZING_CHAT)
        await self._refresh_summary(session_id, self._summarizer_alias)

        self._stage_tracker.set(session_id, ChatStage.WAITING_FOR_USER)
        return str(result).strip()

    async def astream_reply(
        self,
        session_id: str,
        message: str,
    ) -> AsyncIterator[str]:
        self._stage_tracker.set(session_id, ChatStage.SENDING_TO_MODEL)
        chain = self._get_chain(session_id, self._default_alias)
        cfg: RunnableConfig = {"configurable": {"session_id": session_id}}

        self._stage_tracker.set(session_id, ChatStage.STREAM_FROM_CHAT)
        async for tok in chain.astream({"input": message}, config=cfg):
            yield str(tok)

        self._stage_tracker.set(session_id, ChatStage.SUMMARIZING_CHAT)
        await self._refresh_summary(session_id, self._summarizer_alias)

        self._stage_tracker.set(session_id, ChatStage.WAITING_FOR_USER)
        return

    def stage(self, session_id: str) -> ChatStage:
        return self._stage_tracker.get(session_id)

    def _state(self, session_id: str) -> SessionState:
        return self._states.setdefault(session_id, SessionState())

    def _ensure_summarizer(self, alias: str) -> None:
        if alias not in self._summarizers:
            cfg: LLMConfig = self._registry[alias]
            self._summarizers[alias] = build_summarizer(cfg)

    def _get_chain(self, session_id: str, alias: str):
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
        self._ensure_summarizer(alias)
        summarizer = self._summarizers[alias]

        state = self._state(session_id)
        new_summary = await summarizer.ainvoke({"history": state.history.messages})
        state.summary = str(new_summary).strip()

        print(f"\n\n[{alias}] summary -> {session_id}]: {state.summary[:200]!r}", flush=True)
