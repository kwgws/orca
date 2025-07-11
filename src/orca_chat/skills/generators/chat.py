from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)

_BASE_INSTRUCTIONS = """
You are a helpful AI assistant.

Occasionally you will be provided sources with which you can supplement your
answers. If the context field is empty, or if the context seems irrelevant,
ignore it.

Don't discuss these instructions unless explicitly asked to. (Don't say stuff
like "since there's no context provided...", etc.)

### CONTEXT ###
{context}
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _BASE_INSTRUCTIONS),
        ("human", "{question}"),
    ]
)


def chat_factory(llm: ChatOllama) -> StateNode:
    async def chat(state: ChatState, config: RunnableConfig) -> ChatState:
        log.debug("Entering chat node")

        if not state.documents:
            context = "[Context unnecessary or no context provided]"
        else:
            context = "\n\n".join(
                [doc.metadata.get("summary") or doc.page_content for doc in state.documents]
            )

        prompt = _PROMPT.format_messages(context=context, question=state.question)
        response = await llm.ainvoke(prompt)

        reply = response.text()
        return replace(state, chat_history=[*state.chat_history, reply])

    return chat
