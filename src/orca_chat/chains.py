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


def _get_prompt_template(cfg: LLMConfig, precis: str) -> ChatPromptTemplate:
    """SystemMessage is either the running precis or the static system prompt."""
    system = cfg.system.strip() or "You are a helpful AI assistant."
    if precis:
        system += f"\n\n\nHere is a short summary of the conversation so far: {precis}"

    return ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system),
            MessagesPlaceholder("history"),
            HumanMessagePromptTemplate.from_template("{input}"),
        ]
    )


def build_llm(
    cfg: LLMConfig,
    precis: str,
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
    core: Runnable = _get_prompt_template(cfg, precis) | llm | StrOutputParser()

    if retriever:
        hist_aware = create_history_aware_retriever(llm, retriever)
        core = create_retrieval_chain(hist_aware, core)

    return core


def build_editor_llm(cfg: LLMConfig) -> Runnable:
    """Return a runnable that condenses full chat history into a short prècis."""
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
            SystemMessage(
                "Summarize this conversation in a 250-word précis of no more than 250 words."
            ),
            MessagesPlaceholder("history"),
            AIMessage(content="Précis:"),
        ]
    )
    return prompt | llm | StrOutputParser()
