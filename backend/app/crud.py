"""
crud.py
Reusable database operations, including the Accept/Override
evaluation-decision logging used for RQ4 data collection.
"""

from sqlalchemy.orm import Session
from backend.app.models import EvaluationDecision


def record_decision(
    db: Session,
    ac_id: str,
    tc_id: str,
    decision: str,          # "accept" or "override"
    reason: str = "",
    participant_id: str = "anonymous",
):
    """Save one Accept/Override decision from an evaluation session."""
    entry = EvaluationDecision(
        ac_id=ac_id,
        tc_id=tc_id,
        decision=decision,
        reason=reason,
        participant_id=participant_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_decisions(db: Session, participant_id: str = None):
    """Retrieve all recorded decisions, optionally filtered by participant."""
    query = db.query(EvaluationDecision)
    if participant_id:
        query = query.filter(EvaluationDecision.participant_id == participant_id)
    return query.all()


def clear_decisions(db: Session, participant_id: str = None):
    """Delete recorded decisions - useful for resetting between pilot sessions."""
    query = db.query(EvaluationDecision)
    if participant_id:
        query = query.filter(EvaluationDecision.participant_id == participant_id)
    count = query.delete()
    db.commit()
    return count