from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)

_INSTRUCTIONS = """
You are an editor. Your job is to clarify and disambiguate the user input
below before it is passed to an AI chatbot as part of a prompt. Use the
context, chat summary, and chat history below, if provided, to ensure questions,
references, and pronouns are made as straightforward and explicit as possible.
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "## INSTRUCTIONS ##\n{instructions}"),
        ("system", "## CONTEXT ##\n{context}"),
        ("system", "## SUMMARY ##\n{summary}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}"),
    ]
)


def disambiguator_factory(llm: ChatOllama) -> StateNode:
    async def disambiguate(state: ChatState, config: RunnableConfig) -> ChatState:
        log.info("Entering disambiguator node")
        if not state.question:
            raise ValueError("Disambiguator called but no question provided")

        prompt = _PROMPT.format_messages(
            instructions=_INSTRUCTIONS,
            context=state.get_documents_str() or "N/A",
            summary=state.summary or "N/A",
            chat_history=state.chat_history,
            question=state.question,
        )
        response = await llm.ainvoke(prompt)

        disambiguation = response.text().strip()
        log.info("Disambiguator received reply")
        return replace(
            state,
            disambiguation=disambiguation,
        )

    return disambiguate
