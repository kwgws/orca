"""orca_chat/skills/rank.py"""

import json
from logging import getLogger
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ..core.session import ChatSession
from ..loaders import LLMConfig, load_config

log = getLogger(__name__)

_CONFIG = load_config()
_MAX_DOCS: int = _CONFIG.llm.max_docs_to_llm


def build(cfg: LLMConfig, *, llm: ChatOllama, **kwargs) -> StateNode:
    async def _rank(state: ChatSession, config: RunnableConfig) -> dict[str, Any]:
        log.info("Entering node 'rank'")

        documents = state.payload.get("documents", [])
        if not documents or not isinstance(documents, list):
            log.warning("No documents to rank")
            return {}

        prompt = cfg.prompt.format_messages(
            context=state.get_context(),
            chat_history=state.get_abridged_history(),
            input=state.get_last_message(),
        )

        tokens: list[str] = []
        async for chunk in llm.astream(prompt, config=config):
            tokens.append(str(chunk.content) or "")

        ai_message = "".join(tokens)
        try:
            data = json.loads(ai_message)
            norm = [[int(x) for x in pair] for pair in data]
            rank = sorted(norm, key=lambda doc: doc[1])
            docs = [documents[i] for i, score in rank if score > 2]
        except Exception as e:
            log.warning("Error during JSON handling: %s", e)
            docs = documents

        docs = docs[:_MAX_DOCS]

        for i, doc in enumerate(docs):
            title = doc.metadata.get("title", "") or doc.metadata.get("source", "<no title>")
            log.info("Rank #%d: %s", i, title)

        return {"payload": {**state.payload, "documents": docs}}

    return _rank
