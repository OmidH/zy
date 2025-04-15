from typing import Dict, Any
from pydantic import BaseModel

from ..datamodel.message import MessageModel


class StateItem(BaseModel):
    question: MessageModel
    answer: MessageModel
    system: Dict[str, Any]
