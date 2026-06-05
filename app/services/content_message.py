from dataclasses import dataclass
from datetime import datetime


@dataclass
class ContentMessage:
    text: str
    source: str
    date: datetime
    message_id: str
    post_url: str
