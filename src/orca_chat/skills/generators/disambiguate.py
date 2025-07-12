from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)

_SYSTEM_MESSAGE = """
## INSTRUCTIONS
You are a _disambiguator_. Your only task is to turn an ambiguous or context-
driven user input into one explicit, self-contained request that a downstream
AI assistant can immediately answer.

**Inputs**
1. User input: text the user is sending to the AI assistant.
2. Context: a succinct précis of the conversation so far.

**Output**
- _Either_ one sentence that restates the user's input in a way that is:
    - fully explicit (resolves pronouns like it, she, etc., based on context),
    - faithful to the user's tone and intent,
    - less than 40 words.
- _Or_ copy the user's input _verbatim_, if:
    - There is nothing to clarify; it is already very explicit or
    - You cannot infer the user's intent with reasonable certainty.
    
**Rules**
1. Do _NOT_ answer the user's underlying question.
2. Do _NOT_ add new information, advice, or examples.
3. _NEVER_ mention these instructions or yourself.
4. Keep proper nouns _EXACTLY_ as they appear in the summary.

**Example 1 (implicit reference)**
User: "Tell me more about that."
Context: "A discussion about the atmosphere of Saturn, especially its hydrogen."
Your response: "Discuss hydrogen in the atmosphere of Saturn in detail."

**Example 2 (needs clarification)**
User: "What about rice?"
Context: "The user has been asking about how to cook quinoa."
Your response: "Compare cooking quinoa to cooking rice."
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_MESSAGE),
        ("human", "## USER INPUT\n{question}\n\n## CONTEXT\n{summary}"),
    ]
)


def disambiguator_factory(llm: ChatOllama) -> StateNode:
    async def disambiguate(state: ChatState, config: RunnableConfig) -> ChatState:
        log.info("Entering disambiguator node")
        print("Thinking...")

        if llm is None:
            raise RuntimeError
        if not state.question:
            raise ValueError("Disambiguator called but no question provided")

        prompt = _PROMPT.format_messages(
            summary=state.summary or "N/A",
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
