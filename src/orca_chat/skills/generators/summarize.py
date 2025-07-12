from dataclasses import replace
from logging import getLogger

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)

_HISTORY_MAX_LENGTH = 6
_SYSTEM_MESSAGE = """
## INSTRUCTIONS
You are an _editor_. Your job is to write a clean, accurate, and concise précis
summarizing the conversation so far. Imagine you are writing notes for yourself.
Be careful; explicit. High signal, low noise.

**Output**
A single-paragraph précis of the conversation, which:
- is about 120 words; fewer if the conversation is short, more if it is long,
- includes all relevant topics, key facts, and open questions,
- highlights nuances of tone etc. where they might be useful to the assistant,
- contains no editorializations or inventions,
- and is phrased in neutral, descriptive language.

**Rules**
1. Do _NOT_ respond to or interact with the conversation itself.
2. Do _NOT_ include reasoning, thought process, headings, labels, etc.
3. If your last summary is provided, use it for reference but do _NOT_ copy
    it verbatim or rely too heavily on its assumptions.

**Example 1**
The discussion is about the early phases of the French Revolution, focusing on
Louis XVI's mounting fiscal crisis and Marie Antoinette's tarnished public
image. The assistant explained how Abbé Sieyès and Jacques Necker pressured the
king to convene the Estates-General at Versailles in May 1789. The user asked
about the symbolic impact of the Bastille's fall on 14 July 1789, prompting
details about the prison's garrison and Parisian fears of royal reprisals.
Conversation then shifted to the drafting of the Declaration of the Rights of
Man by Lafayette (with input from Thomas Jefferson) and its reverberations
across the Atlantic World.

**Example 2**
The conversation is about time management. The user mentioned they struggle
with ADHD and executive function. The assistant explained the Pomodoro Method
and asked if there were any specific tasks the user needed help planning.
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_MESSAGE),
        ("user", "## YOUR LAST SUMMARY\n{summary}\n\n## CHAT HISTORY\n{history}"),
    ]
)


def summarizer_factory(llm: ChatOllama) -> StateNode:
    async def summarize(state: ChatState, config: RunnableConfig) -> ChatState:
        log.info("Entering summarizer node")
        if not state.chat_history:
            raise ValueError("Summarizer node called but no chat history provided")

        trimmed_history = state.chat_history[-_HISTORY_MAX_LENGTH:]
        history = "\n".join(
            f"{msg.type.upper()}: {msg.content}"
            for msg in trimmed_history
        )  # fmt: skip

        prompt = _PROMPT.format_messages(
            summary=state.summary or "N/A",
            history=history,
        )

        node_config: RunnableConfig = {
            **config,
            "tags": [*(config.get("tags", [])), "summarize_node"],
        }
        response = await llm.ainvoke(prompt, config=node_config)

        summary = str(response.content).strip()
        log.info("Summarizer node received reply")
        return replace(
            state,
            summary=summary,
            chat_history=trimmed_history,
        )

    return summarize
