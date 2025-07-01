from enum import Enum, auto


class ChatStage(Enum):
    WAITING_FOR_USER = auto()
    SENDING_TO_MODEL = auto()
    STREAM_FROM_CHAT = auto()
    SUMMARIZING_CHAT = auto()


class StageTracker:
    def __init__(self) -> None:
        self._stages: dict[str, ChatStage] = {}

    def set(self, session_id: str, stage: ChatStage) -> None:
        self._stages[session_id] = stage
        print(f"[stage → {session_id}]: {stage.name}", flush=True)

    def get(self, session_id: str) -> ChatStage:
        return self._stages.get(session_id, ChatStage.WAITING_FOR_USER)
