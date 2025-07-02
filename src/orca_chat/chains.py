from httpx import Timeout
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable
from langchain_ollama import ChatOllama

from orca_chat.config import LLMConfig

__all__ = [
    "build_chat_core",
    "build_summarizer",
    "chat_prompt",
]


def build_summarizer(cfg: LLMConfig) -> Runnable:
    """Return a runnable that condenses full chat history into < 250 words."""
    llm = ChatOllama(
        base_url=cfg.base_url,
        client_kwargs={"timeout": Timeout(cfg.timeout_s)},
        **cfg.to_request_dict(),
    ).with_retry(
        stop_after_attempt=5,
        exponential_jitter_params={"initial": 1.0, "max": float(cfg.timeout_s)},
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage("Summarize the conversation so far in < 250 words."),
            MessagesPlaceholder("history"),
            AIMessage(content="Summary:"),
        ]
    )
    return prompt | llm | StrOutputParser()


def chat_prompt(cfg: LLMConfig, summary: str) -> ChatPromptTemplate:
    """SystemMessage is either the running summary or the static system prompt."""
    return ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                content=summary if summary else cfg.system or "You are a helpful AI assistant."
            ),
            MessagesPlaceholder("history"),
            HumanMessagePromptTemplate.from_template("{input}"),
        ]
    )


def build_chat_core(
    cfg: LLMConfig,
    summary: str,
    retriever: BaseRetriever | None,
) -> Runnable:
    """Assemble prompt → LLM → parser, optionally wrapped with retrieval."""
    llm = ChatOllama(
        base_url=cfg.base_url,
        client_kwargs={"timeout": Timeout(cfg.timeout_s)},
        **cfg.to_request_dict(),
    ).with_retry(
        stop_after_attempt=5,
        exponential_jitter_params={"initial": 1.0, "max": float(cfg.timeout_s)},
    )
    core: Runnable = chat_prompt(cfg, summary) | llm | StrOutputParser()

    if retriever:
        hist_aware = create_history_aware_retriever(llm, retriever)
        core = create_retrieval_chain(hist_aware, core)

    return core
