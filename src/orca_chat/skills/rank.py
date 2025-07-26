"""orca_chat/skills/rank.py"""

import json
from logging import getLogger
from typing import Any

from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ..core.session import ChatSession
from ..loaders import LLMConfig

log = getLogger(__name__)


def build(cfg: LLMConfig, *, llm: ChatOllama, **kwargs) -> StateNode:
    async def _rank(state: ChatSession, config: RunnableConfig) -> dict[str, Any]:
        log.info("Entering node 'rank'")
        node_config: RunnableConfig = {
            **config,
            "tags": [*(config.get("tags", [])), "node_rank"],
        }

        documents: list[Document] = state.payload.get("documents", [])
        if not documents:
            log.warning("No documents to rank")
            return {}

        prompt = cfg.prompt.format_messages(
            context=state.get_documents(
                max_docs=20,
                max_doc_length=100,
                prefer_summary=True,
            ),
            input=state.payload.get("topic") or state.get_last_message(),
        )

        tokens: list[str] = []
        async for chunk in llm.astream(prompt, config=node_config):
            tokens.append(str(chunk.content) or "")
        ai_message = "".join(tokens)

        try:
            data = json.loads(ai_message)
            norm = [[int(x) for x in pair] for pair in data]
            rank = sorted(norm, key=lambda doc: doc[1], reverse=True)
            docs = [documents[i] for i, score in rank if score > 2]
        except Exception as e:
            log.warning("Error during JSON handling: %s", e)
            docs = documents

        for i, doc in enumerate(docs):
            title = doc.metadata.get("title", "") or doc.metadata.get("source", "<no title>")
            log.info("Rank #%d: %s", i, title)
        return {"payload": {**state.payload, "documents": docs}}

    return _rank
