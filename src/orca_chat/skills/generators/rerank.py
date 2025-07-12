import json
from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)

_RERANKER_IN_MAX_DOCS = 10
_RERANKER_IN_MAX_CHARS = 300
_RERANKER_OUT_MAX_DOCS = 3

_SYSTEM_MESSAGE = """
## INSTRUCTIONS
You are a _relevance scorer_. Given a research question, a search query, and an
indexed list of documents, you assign each document a relevance score from
0 (utterly irrelevant) to 10 (answers question explicitly).

**Inputs**
1. Documents: an indexed list of documents, each with a summary or sample text.
2. Query: the search query used to find these documents.
3. Question: the question or discussion that led to the search.

**Output**
A single-line JSON array of `[index, score]` pairs, one pair for each document.
Scores must be whole numbers from 0 to 10, no decimals.

**Rules**
1. Output _NOTHING_ except the single-line JSON string.
2. Do _NOT_ explain, comment, or add keys or labels.
3. If no documents are provided, return `[]`.

**Example 1**
Question: "What would it be like to live on the moons of Mars?"
Query: "Moons of Mars"
Documents: "[0] Galilean Moons, [1] Deimos, [2] Mars (Planet)"
Your response: "[[0, 2], [1, 9], [2, 8]]"

**Example 2**
Question: "Summarize the plot of Pride and Prejudice"
Query: "Pride and Prejudice (1813 novel)"
Documents: "[0] Jane Austen, [1] English Reformation, [2] Pride and Prejudice"
Your response: "[[0, 8], [1, 1], [2, 10]]
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_MESSAGE),
        ("human", "## QUESTION\n{question}\n\n## QUERY\n{query}\n\n## DOCUMENTS\n{context}"),
    ]
)


def reranker_factory(llm: ChatOllama) -> StateNode:
    async def rerank(state: ChatState, config: RunnableConfig) -> ChatState:
        print("Thinking...")
        log.info("Entering reranker node")
        if not state.documents:
            raise ValueError("Reranker called but no documents provided")
        if not state.search_query:
            raise ValueError("Reranker called but no search query provided")
        if not (state.disambiguation or state.question):
            raise ValueError("Reranker called but no question provided")

        prompt = _PROMPT.format_messages(
            context=state.get_documents_str(
                max_chars=_RERANKER_IN_MAX_CHARS, max_documents=_RERANKER_IN_MAX_DOCS
            ),
            query=state.search_query,
            question=state.disambiguation or state.question,
        )
        response = await llm.ainvoke(prompt)
        json_str = response.text().strip()

        try:
            data = json.loads(json_str)
            norm = [[int(x) for x in pair] for pair in data][:_RERANKER_OUT_MAX_DOCS]
            rank = sorted(norm, key=lambda doc: doc[0])
            docs = [state.documents[i] for i, score in rank if score > 2]
        except Exception as e:
            log.warning("Error during JSON handling: %s", e)
            docs = state.documents

        for i, doc in enumerate(docs):
            log.info("Result %d: %s", i, doc.metadata.get("source") or "unknown")
        return replace(
            state,
            documents=docs,
        )

    return rerank
