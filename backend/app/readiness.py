from sqlalchemy.orm import Session
from backend.app.models import (
    Feature,
    AcceptanceCriteria,
    TestCase,
    Traceability,
    Deployment,
)

def calculate_readiness(feature_id: str, db: Session):

    score = 0
    recommendations = []

    feature = db.query(Feature).filter(
        Feature.feature_id == feature_id
    ).first()

    if feature is None:
        return {"error": "Feature not found"}

    if db.query(AcceptanceCriteria).filter(
        AcceptanceCriteria.feature_id == feature_id
    ).count():
        score += 25
    else:
        recommendations.append("Acceptance Criteria missing")

    tests = db.query(TestCase).filter(
        TestCase.feature_id == feature_id
    ).all()

    if tests:
        passed = sum(1 for t in tests if t.result.lower() == "pass")

        if passed == len(tests):
            score += 25
        else:
            recommendations.append("Some test cases failed")
    else:
        recommendations.append("No test cases")

    trace = db.query(Traceability).filter(
        Traceability.feature_id == feature_id
    ).all()

    if trace:
        linked = sum(1 for t in trace if t.status.lower() == "linked")

        if linked == len(trace):
            score += 25
        else:
            recommendations.append("Broken traceability")
    else:
        recommendations.append("Traceability missing")

    deploy = db.query(Deployment).filter(
        Deployment.feature_id == feature_id
    ).first()

    if deploy and deploy.status.lower() == "ready":
        score += 25
    else:
        recommendations.append("Deployment not ready")

    return {
        "feature_id": feature.feature_id,
        "feature_name": feature.feature_name,
        "readiness_score": score,
        "status":
            "Ready" if score >= 90 else
            "Partially Ready" if score >= 60 else
            "Not Ready",
        "recommendations": recommendations
    }