from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)

_INSTRUCTIONS = """
Read the question below and the chat summary/history, if provided. Respond
with **one concise, natural-language search phrase**.
Do not use flags or boolean operators** (site:, intitle:, OR, etc).
Return _only_ your search as written. Do not include an explanation.

### EXAMPLES ###
- Q: Tell me about the Warren Court.
  A: U.S. Supreme Court under Chief Justice Earl Warren
- Q: What are Miranda rights?
  A: Miranda v. Arizona and the right to silence
- Q: Let's talk about Disney's Little Mermaid.
  A: Little Mermaid, 1989 Disney film
- Q: What do you know about the Little Mermaid?
  A: Little Mermaid, Hans Christian Andersen fairy tale
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "## INSTRUCTIONS ##\n{instructions}"),
        ("system", "## SUMMARY ##\n{summary}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}"),
    ]
)


def searchifier_factory(llm: ChatOllama) -> StateNode:
    async def searchify(state: ChatState, config: RunnableConfig) -> ChatState:
        log.info("Entering searchifier node")
        if not (state.disambiguation or state.question):
            raise ValueError("Searchifier node called but no question provided")

        prompt = _PROMPT.format_messages(
            instructions=_INSTRUCTIONS,
            summary=state.summary or "N/A",
            chat_history=state.chat_history,
            question=state.disambiguation or state.question,
        )
        response = await llm.ainvoke(prompt)

        search_query = response.text().strip()
        log.info("Searchifier wrote query: %s", search_query)
        return replace(
            state,
            search_query=search_query,
        )

    return searchify
