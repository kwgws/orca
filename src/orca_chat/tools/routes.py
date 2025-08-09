# orca_chat/tools/routes.py

from typing import Final

from langchain_core.tools import tool

__all__: Final = [
    "route_to_archive_retriever",
    "route_to_chat",
    "route_to_secondary_source_retriever",
    "route_to_wikipedia",
]


@tool
def route_to_archive_retriever() -> str:
    """Route message to the archive retriever.

    When to use
    -----------
    Choose this route when the user wants original Warren Court materials:
    case files, drafts, memos, correspondence, docket sheets, conference notes,
    oral-argument material, chamber papers, internal circulations, handwritten
    annotations, clippings, diary entires, etc.

    Positive cues
    -------------
    - Mentions of specific cases (e.g. Brown v. Board, Gideon, Miranda, etc.)
      with intent to view internal documents or case materials.
    - Requests using verbs like find, locate, show, pull, retrieve _from the
      archive_ or _in Brennan's/Marshall's papers_, etc.
    - References to chambers, clerks, docket/box/folder numbers.

    Do NOT use
    ----------
    - High-level overviews, definitions, or historiographical questions
      (prefer the secondary source retriever).
    - Pure background on people, places, statues, or historical context
      generally (prefer Wikipedia).
    - All other messages (prefer chat).

    Returns
    -------
    str
        Literal "archive_retriever"
    """
    return "archive_retriever"


@tool
def route_to_secondary_source_retriever() -> str:
    """Route message to the secondary source retriever.

    When to use
    -----------
    Choose this route for scholarly or interpretive context: law review,
    monographs and biographies, doctrinal analyses, historiography, and
    questions about legacy or meaning.

    Positive cues
    -------------
    - "What do scholars/historians say about ...?"
    - "Finds articles on ..." "literature on..." "a biography of..."
    - Requests to compare scholarly interpretations, schools of thought, or
      citation networks around case(s)/opinion(s).

    Do NOT use
    ----------
    - Direct requests for specific documents (prefer the archive retriever).
    - Basic background, context, and definitions (prefer Wikipedia).
    - All other messages (prefer chat).

    Returns
    -------
    str
        Literal "secondary_source_retriever"
    """
    return "secondary_source_retriever"


@tool
def route_to_wikipedia() -> str:
    """Route message to a Wikipedia search.

    When to use
    -----------
    Choose this for general knowledge and context about people, cases,
    concepts, statues, dates, or timelines. Look for:
    - "Who/what/when/where is ...?"
    - Definitions ("what is incorporation?", "what's the rule in Mapp?").
    - Context for orientation before primary/secondary source research.

    When to NOT use
    ---------------
    - Archive-specific materials (prefer archive retriever).
    - Scholarly/interpretive discussion (prefer secondary source retriever).
    - All other messages (prefer chat).

    Returns
    -------
    str
        Literal "wikipedia"
    """
    return "wikipedia"


@tool
def route_to_chat() -> str:
    """Route to the chat node (fallback, mutually exclusive).

    When to use
    -----------
    - Greetings and pleasantries.
    - Vague or underspecified asks that need clarification.
    - Open conversation, planning, or meta questions.
    - Anything unrelated to legal history.
    - Any time you are less than 90% confident that a retriever is needed.

    Do NOT use
    ----------
    - Together with **ANY** retriever tools. This route is mutually exclusive.
    - When a retriever's criteria are clearly satisfied.

    Examples
    --------
    - "Hello!"
    - "Can you help me figure out my approach?"
    - "What can you do?"

    Returns
    -------
    str
        Literal "chat".
    """
    return "chat"
