from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)

_HISTORY_MAX_LENGTH = 6
_INSTRUCTIONS = """
You are an editor. Your job is to write a short précis summarizing the
following conversation. Be concise, but don't lose track of any key facts
or crucial details.
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "## INSTRUCTIONS ##\n{instructions}"),
        ("system", "## YOUR LAST SUMMARY ##\n{summary}"),
        MessagesPlaceholder("chat_history"),
    ]
)


def summarizer_factory(llm: ChatOllama) -> StateNode:
    async def summarize(state: ChatState, config: RunnableConfig) -> ChatState:
        log.info("Entering summarizer node")
        if not state.chat_history:
            raise ValueError("Summarizer node called but no chat history provided")

        prompt = _PROMPT.format_messages(
            instructions=_INSTRUCTIONS,
            summary=state.summary or "N/A",
            chat_history=state.chat_history,
        )
        response = await llm.ainvoke(prompt)

        summary = response.text().strip()
        trimmed_history = state.chat_history[-_HISTORY_MAX_LENGTH:]
        log.info("Summarizer node received reply")
        return replace(
            state,
            summary=summary,
            chat_history=trimmed_history,
        )

    return summarize
