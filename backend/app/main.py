from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal, engine
from backend.app import models, schemas, crud
from backend.app.readiness import calculate_readiness
from backend.app.ai import infer_missing_links, detect_stale_links, run_full_assessment

# Create database tables (only creates tables that don't already exist,
# so this is safe to re-run - it will add the new evaluation_decisions
# table without touching your existing 5 tables or their data)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI-Assisted Feature Readiness Assessment",
    version="1.0.0"
)

# -------------------------
# CORS Configuration
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def home():
    return {
        "message": "AI-Assisted Feature Readiness Assessment"
    }


# -------------------------
# Existing data endpoints
# -------------------------

@app.get("/features")
def get_features(db: Session = Depends(get_db)):
    return db.query(models.Feature).all()


@app.get("/acceptance-criteria")
def get_acceptance(db: Session = Depends(get_db)):
    return db.query(models.AcceptanceCriteria).all()


@app.get("/test-cases")
def get_tests(db: Session = Depends(get_db)):
    return db.query(models.TestCase).all()


@app.get("/traceability")
def get_traceability(db: Session = Depends(get_db)):
    return db.query(models.Traceability).all()


@app.get("/deployment")
def get_deployment(db: Session = Depends(get_db)):
    return db.query(models.Deployment).all()


@app.get("/readiness/{feature_id}")
def readiness(feature_id: str, db: Session = Depends(get_db)):
    return calculate_readiness(feature_id, db)


# -------------------------
# NEW: AI endpoints (RQ2 and RQ3)
# -------------------------

@app.get("/ai/infer-missing-links")
def ai_infer_missing_links(feature_id: str = None, db: Session = Depends(get_db)):
    """RQ2: propose links for acceptance criteria with no explicit
    traceability entry, using TF-IDF semantic similarity."""
    return infer_missing_links(db, feature_id)


@app.get("/ai/detect-stale-links")
def ai_detect_stale_links(feature_id: str = None, db: Session = Depends(get_db)):
    """RQ3: flag traceability links that appear stale because the
    linked test case matches the requirement's OLD wording more
    closely than its current wording."""
    return detect_stale_links(db, feature_id)


@app.get("/ai/assessment")
def ai_full_assessment(feature_id: str = None, db: Session = Depends(get_db)):
    """Both RQ2 and RQ3 results together - this is what the Trace Map
    / dashboard view should call to render the full picture."""
    return run_full_assessment(db, feature_id)


# -------------------------
# NEW: Evaluation endpoints (RQ4 - Accept/Override data collection)
# -------------------------

@app.post("/evaluation/decision", response_model=schemas.DecisionOut)
def submit_decision(decision: schemas.DecisionCreate, db: Session = Depends(get_db)):
    """Record one Accept/Override decision from a participant during
    an evaluation session. This is the primary data source for RQ4."""
    return crud.record_decision(
        db,
        ac_id=decision.ac_id,
        tc_id=decision.tc_id,
        decision=decision.decision,
        reason=decision.reason,
        participant_id=decision.participant_id,
    )


@app.get("/evaluation/decisions", response_model=list[schemas.DecisionOut])
def list_decisions(participant_id: str = None, db: Session = Depends(get_db)):
    """Retrieve recorded decisions, optionally filtered to one participant."""
    return crud.get_decisions(db, participant_id)


@app.delete("/evaluation/decisions")
def reset_decisions(participant_id: str = None, db: Session = Depends(get_db)):
    """Clear recorded decisions - use between pilot participants."""
    count = crud.clear_decisions(db, participant_id)
    return {"deleted": count}