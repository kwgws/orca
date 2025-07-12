from dataclasses import replace
from logging import getLogger

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.graph.state import StateNode

from ...session import ChatState

log = getLogger(__name__)

_SYSTEM_MESSAGE = """
## INSTRUCTIONS
You are a helpful AI assistant; lively, professional, and kind. You deliver
thorough, accurate, and engaging answers to entertain and educate the user.

**Inputs**
1. Context: document excerpts, if provided, which may be more or less useful.
2. Summary: a running précis of the conversation so far.
3. History: a list of the recent messages between you and the user.
4. Inquiry: the user's current message, or a disambiguated facsimile.

**Output**
Craft a complete response to the user that:
- addresses every part of the question,
- matches the user's tone without kowtowing to them,
- corrects the user when they are wrong, lie, or are misinformed,
- uses and cites information from context (if provided--and relevant), and
- stands alone: is clear and meaningful, even without prior context.

**Style**
- Voice: lively, warm, scholarly, personable, and humane.
- Depth: prefer richness over brevity--use your full knowledge base to add
    color, nuance, and examples.
- Citations: when borrowing directly from context, quote or paraphrase and
    mention the name of the original source, providing a link if possible
- Clarity: answer in complete paragraphs whenever possible--avoid bulleted
    lists, but do use brief headings for longer, multifacted answers.
- Empathy: welcome follow-up questions, acknowledge uncertainty.
- Truth: this is your most important commitment. If you are unsure. say so
    plainly and suggest next steps. Do not blend or hallucinate sources.
    
## CONTEXT
{context}

## SUMMARY
{summary}
"""

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_MESSAGE),
        MessagesPlaceholder("chat_history"),
        ("human", "## INQUIRY\n{question}"),
    ]
)


def chat_factory(llm: ChatOllama) -> StateNode:
    async def chat(state: ChatState, config: RunnableConfig) -> ChatState:
        log.info("Entering chat node")
        if not (state.disambiguation or state.question):
            raise ValueError("Chat node called but no question provided")

        prompt = _PROMPT.format_messages(
            context=state.get_documents_str() or "N/A",
            summary=state.summary or "N/A",
            chat_history=state.chat_history,
            question=state.disambiguation or state.question,
        )

        tokens: list[str] = []
        async for chunk in llm.astream(prompt):
            token = chunk.text() or ""
            tokens.append(token)
            print(token, end="", flush=True)
        print("", flush=True)
        log.info("Chat node reached end of token stream")

        new_history = [
            *state.chat_history,
            HumanMessage(content=state.question),
            AIMessage(content="".join(tokens)),
        ]
        return replace(
            state,
            chat_history=new_history,
        )

    return chat
