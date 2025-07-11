from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)

_BASE_INSTRUCTIONS = """
You are a router. Your job is to route the user's question to the appropriate
node. Read the question below, then answer with a single word:

- "none" if the question is simple and direct, if it concerns something
  specific from earlier in the conversation, or if it is something that can
  be answered with basic knowledge.
  
- "wiki" if the question involves current events, scholarly inquiry, or
  specific people or data, or if the question otherwise seems best answered
  by reference to Wikipedia.

### EXAMPLES ###
- Q: "Hello!"
  A: none
- Q: "Tell me about yourself."
  A: none
- Q: "Tell me about the history of the U.S. Supreme Court."
  A: wiki
- Q: "Reframe through those instructions as a bulleted list."
  A: none
- Q: "Why does the Sun set in the West?"
  A: none
- Q: "Why was the Little Mermaid such a successful film?"
  A: wiki
  
**IMPORTANT:** Do _not_ explain your reasoning or include any other context.
Respond _only_ with the word "wiki" or the word "none."
\n\n
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _BASE_INSTRUCTIONS),
        ("human", "{question}"),
    ]
)


def router_factory(llm: ChatOllama) -> StateNode:
    async def route(state: ChatState, config: RunnableConfig) -> ChatState:
        log.info("Entering router node")
        prompt = _PROMPT.format_messages(question=state.question)

        response = await llm.ainvoke(prompt)
        choice = response.text().strip().lower()
        log.info("Router chose: %s", choice)

        return replace(state, router_flags=choice)

    return route
