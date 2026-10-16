import pandas as pd

from backend.app.database import SessionLocal, engine
from backend.app import models
from backend.app.models import (
    Feature,
    AcceptanceCriteria,
    TestCase,
    Traceability,
    Deployment,
    RequirementHistory,
)

# Create all tables if they don't exist
models.Base.metadata.create_all(bind=engine)


def load_features(db):
    df = pd.read_csv("dataset/features.csv")

    for _, row in df.iterrows():
        existing = db.query(Feature).filter(
            Feature.feature_id == row["feature_id"]
        ).first()

        if existing:
            continue

        db.add(
            Feature(
                feature_id=row["feature_id"],
                feature_name=row["feature_name"],
                sprint=row["sprint"],
                product_owner=row["product_owner"],
            )
        )

    db.commit()
    print("Features loaded")


def load_acceptance(db):
    df = pd.read_csv("dataset/acceptance_criteria.csv")

    for _, row in df.iterrows():
        existing = db.query(AcceptanceCriteria).filter(
            AcceptanceCriteria.ac_id == row["ac_id"]
        ).first()

        if existing:
            continue

        db.add(
            AcceptanceCriteria(
                ac_id=row["ac_id"],
                feature_id=row["feature_id"],
                description=row["description"],
                version=row["version"],
            )
        )

    db.commit()
    print("Acceptance Criteria loaded")


def load_testcases(db):
    df = pd.read_csv("dataset/test_cases.csv")

    for _, row in df.iterrows():
        existing = db.query(TestCase).filter(
            TestCase.tc_id == row["tc_id"]
        ).first()

        if existing:
            continue

        db.add(
            TestCase(
                tc_id=row["tc_id"],
                feature_id=row["feature_id"],
                description=row["description"],
                result=row["result"],
            )
        )

    db.commit()
    print("Test Cases loaded")

def load_traceability(db):
    df = pd.read_csv("dataset/traceability.csv")

    for _, row in df.iterrows():
        existing = db.query(Traceability).filter(
            Traceability.feature_id == row["feature_id"],
            Traceability.ac_id == row["ac_id"],
            Traceability.tc_id == row["tc_id"],
        ).first()

        if existing:
            continue

        db.add(
            Traceability(
                feature_id=row["feature_id"],
                ac_id=row["ac_id"],
                tc_id=row["tc_id"],
                status=row["status"],
            )
        )

    db.commit()
    print("Traceability loaded")

def load_deployment(db):
    df = pd.read_csv("dataset/deployment.csv")

    for _, row in df.iterrows():
        existing = db.query(Deployment).filter(
            Deployment.feature_id == row["feature_id"],
            Deployment.environment == row["environment"],
        ).first()

        if existing:
            continue

        db.add(
            Deployment(
                feature_id=row["feature_id"],
                environment=row["environment"],
                status=row["status"],
            )
        )

    db.commit()
    print("Deployment loaded")


def load_requirement_history(db):
    df = pd.read_csv("dataset/requirement_history.csv")

    for _, row in df.iterrows():
        existing = db.query(RequirementHistory).filter(
            RequirementHistory.feature_id == row["feature_id"],
            RequirementHistory.ac_id == row["ac_id"],
        ).first()

        if existing:
            continue

        db.add(
            RequirementHistory(
                feature_id=row["feature_id"],
                ac_id=row["ac_id"],
                old_text=row["old_text"],
                new_text=row["new_text"],
            )
        )

    db.commit()
    print("Requirement History loaded")

def main():
    db = SessionLocal()

    load_features(db)
    load_acceptance(db)
    load_testcases(db)
    load_traceability(db)
    load_deployment(db)
    load_requirement_history(db)

    db.close()

    print("\nAll data successfully imported!")


if __name__ == "__main__":
    main()