"""
schemas.py
Pydantic models for request validation and response shaping.
"""

from pydantic import BaseModel
from typing import Optional


class DecisionCreate(BaseModel):
    ac_id: str
    tc_id: str
    decision: str  # "accept" or "override"
    reason: Optional[str] = ""
    participant_id: Optional[str] = "anonymous"


class DecisionOut(BaseModel):
    id: int
    ac_id: str
    tc_id: str
    decision: str
    reason: str
    participant_id: str

    class Config:
        from_attributes = True