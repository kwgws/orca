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
You are a _searchifier_. Your job is to transform user input into a single,
concise natural-language search phrase that can be used to retrieve high-
quality sources from a retrieval model.

**Inputs**
2. User input: a message from the user, more or less ambiguous.
1. Context: if provided, a précis of the conversation so far, for reference.

**Output**
- Return only one phrase of less than 8 words written in plain English.
- Do _NOT_ use flags, switches, or Boolean operators.
- Do _NOT_ add explanations or extra lines. Respond _ONLY_ with your phrase.

**Rules**
1. Capture the core topic and key descriptors; drop filler words.
2. Use proper/common nouns; disambiguate pronouns.
3. Decide on the most obvious interpretation based on context.
4. Do _NOT_ include any explanation, context, or extra words in your reply.

**Example 1**
User: What are Miranda rights?
You: Miranda v. Arizona right to silence

**Example 2**
User: Let's talk about Disney's Little Mermaid.
You: Little Mermaid 1989 Disney animated film

**Example 3**
User: What do you know about the Little Mermaid?
You: Little Mermaid Hans Christian Andersen fairy tale
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_MESSAGE),
        ("human", "## USER INPUT\n{question}\n\n## CONTEXT\n{summary}"),
    ]
)


def searchifier_factory(llm: ChatOllama) -> StateNode:
    async def searchify(state: ChatState, config: RunnableConfig) -> ChatState:
        log.info("Entering searchifier node")
        if not (state.disambiguation or state.question):
            raise ValueError("Searchifier node called but no question provided")

        prompt = _PROMPT.format_messages(
            summary=state.summary or "N/A",
            question=state.disambiguation or state.question,
        )
        response = await llm.ainvoke(prompt, config=config)

        search_query = response.text().strip()
        log.info("Searchifier wrote query: %s", search_query)
        return replace(
            state,
            search_query=search_query,
        )

    return searchify
