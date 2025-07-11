from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)


_BASE_INSTRUCTIONS = """
You are a researcher. Your job is to consider the question below and write a
search query that would help answer it. Use what you already know to interpret
the question and make sure you don't lose any crucial relevant details.

### EXAMPLES ###
- Q: Tell me about the Warren Court.
  A: Supreme Court of the United States; Earl Warren
- Q: What are Miranda rights?
  A: Miranda v. Arizona; Right to silence
- Q: Let's talk about Disney's Little Mermaid.
  A: Little Mermaid (1989 film), Disney Animation Studios
- Q: What do you know about the Little Mermaid?
  A: Little Mermaid, Hans Christian Andersen
  
**IMPORTANT:** Do _not_ explain your reasoning or include any other context.
Respond _only_ with your query as formulated.
\n\n
"""


_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _BASE_INSTRUCTIONS),
        ("human", "{question}"),
    ]
)


def searchifier_factory(llm: ChatOllama) -> StateNode:
    async def searchify(state: ChatState, config: RunnableConfig) -> ChatState:
        log.debug("Entering rewrite node")
        prompt = _PROMPT.format_messages(question=state.question)

        response = await llm.ainvoke(prompt)
        search_query = response.text().strip()
        log.info("Question rewritten as query: %s", search_query)

        return replace(state, search_query=search_query)

    return searchify
