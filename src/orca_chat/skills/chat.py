"""orca_chat/skills/chat.py"""

from logging import getLogger
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ..core.session import ChatSession
from ..loaders import LLMConfig, load_config

log = getLogger(__name__)

_CONFIG = load_config()
_DOC_FORMAT_STR: str = _CONFIG.llm.doc_format_str


def build(cfg: LLMConfig, *, llm: ChatOllama, **kwargs) -> StateNode:
    async def _chat(state: ChatSession, config: RunnableConfig) -> dict[str, Any]:
        log.info("Entering node 'chat'")
        node_config: RunnableConfig = {
            **config,
            "tags": [*(config.get("tags", [])), "node_chat", "out_stream"],
        }

        context = state.payload.get("context", "N/A")
        docs = state.payload.get("documents", [])
        if docs and isinstance(docs, list):
            context = "\n\n\n---\n\n\n".join(
                _DOC_FORMAT_STR.format(
                    index=i,
                    title=doc.metadata.get("title", "<no title>"),
                    url=doc.metadata.get("source", "<no url>"),
                    context=doc.page_content,
                )
                for i, doc in enumerate(docs)
            )

        prompt = cfg.prompt.format_messages(
            chat_history=state.get_abridged_history(),
            context=context,
            input=state.get_last_message(),
        )

        tokens: list[str] = []
        async for chunk in llm.astream(prompt, config=node_config):
            tokens.append(str(chunk.content) or "")

        ai_message = ("assistant", "".join(tokens))
        return {"history": [*state.history, ai_message]}

    return _chat
