from sqlalchemy import Column, Integer, String
from .database import Base


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, index=True)
    feature_id = Column(String, unique=True, index=True)
    feature_name = Column(String)
    sprint = Column(String)
    product_owner = Column(String)


class AcceptanceCriteria(Base):
    __tablename__ = "acceptance_criteria"

    id = Column(Integer, primary_key=True, index=True)
    ac_id = Column(String, unique=True)
    feature_id = Column(String)
    description = Column(String)
    version = Column(Integer)


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    tc_id = Column(String, unique=True)
    feature_id = Column(String)
    description = Column(String)
    result = Column(String)


class Traceability(Base):
    __tablename__ = "traceability"

    id = Column(Integer, primary_key=True, index=True)
    feature_id = Column(String)
    ac_id = Column(String)
    tc_id = Column(String)
    status = Column(String)


class Deployment(Base):
    __tablename__ = "deployment"

    id = Column(Integer, primary_key=True, index=True)
    feature_id = Column(String)
    environment = Column(String)
    status = Column(String)


class RequirementHistory(Base):
    __tablename__ = "requirement_history"

    id = Column(Integer, primary_key=True, index=True)
    feature_id = Column(String)
    ac_id = Column(String)
    old_text = Column(String)
    new_text = Column(String)


class EvaluationDecision(Base):
    """NEW TABLE - records Accept/Override decisions from evaluation
    sessions, used for RQ4 data collection (thematic analysis input)."""
    __tablename__ = "evaluation_decisions"

    id = Column(Integer, primary_key=True, index=True)
    ac_id = Column(String)
    tc_id = Column(String)
    decision = Column(String)       # "accept" or "override"
    reason = Column(String)
    participant_id = Column(String)