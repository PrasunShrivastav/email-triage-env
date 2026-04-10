from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


class Email(BaseModel):
    id: str
    subject: str
    sender: str
    sender_email: str
    body: str
    timestamp: datetime
    thread_id: Optional[str] = None
    is_reply: bool = False


class EmailObservation(BaseModel):
    inbox: List[Email]
    current_email: Optional[Email]
    inbox_size: int
    emails_processed: int
    time_elapsed: float
    task_id: str
    task_description: str
    step: int


class EmailAction(BaseModel):
    action_type: Literal[
        "reply",
        "archive",
        "delete",
        "flag",
        "label",
        "forward",
        "mark_urgent",
        "snooze",
        "skip",
    ]
    email_id: str
    content: Optional[str] = None
    label: Optional[str] = None
    forward_to: Optional[str] = None
    snooze_hours: Optional[int] = None


class EmailReward(BaseModel):
    score: float
    cumulative_score: float
    partial_scores: dict
    feedback: str
    done: bool
