from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal, engine
from backend.app import models
from backend.app.readiness import calculate_readiness

# Create database tables
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