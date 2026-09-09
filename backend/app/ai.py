"""
ai.py
The AI-assisted traceability logic.

RQ2 - infer_missing_links():
    For every Acceptance Criterion that has NO row in the Traceability
    table, compare its description against every unlinked Test Case
    description using TF-IDF + cosine similarity, and propose the
    closest match.

RQ3 - detect_stale_links():
    For every Acceptance Criterion that HAS an entry in
    RequirementHistory (i.e. its text changed at some point) and is
    currently linked to a Test Case, compare that Test Case's
    description against the AC's OLD text versus its NEW (current)
    text. If the Test Case matches the OLD text more closely than the
    NEW text, the link is flagged as likely stale: the test still
    reads like it was written for the requirement's earlier wording.

This uses TF-IDF cosine similarity, consistent with information
retrieval techniques discussed in the traceability-recovery literature
(e.g. Alturayeif et al., 2025).
"""

from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.app.models import (
    AcceptanceCriteria,
    TestCase,
    Traceability,
    RequirementHistory,
)

SIMILARITY_THRESHOLD = 0.10


def _similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity between two short texts using TF-IDF."""
    if not text_a or not text_b:
        return 0.0
    try:
        vec = TfidfVectorizer(stop_words="english")
        mat = vec.fit_transform([text_a, text_b])
        return float(cosine_similarity(mat[0:1], mat[1:2])[0][0])
    except ValueError:
        # happens if both texts are empty after stopword removal
        return 0.0


def infer_missing_links(db: Session, feature_id: str = None):
    """RQ2: propose a Test Case for every Acceptance Criterion that has
    no explicit link in the Traceability table. If feature_id is given,
    restrict to that feature only."""

    ac_query = db.query(AcceptanceCriteria)
    if feature_id:
        ac_query = ac_query.filter(AcceptanceCriteria.feature_id == feature_id)
    all_acs = ac_query.all()

    linked_ac_ids = {t.ac_id for t in db.query(Traceability).all()}
    unlinked_acs = [ac for ac in all_acs if ac.ac_id not in linked_ac_ids]

    tc_query = db.query(TestCase)
    if feature_id:
        tc_query = tc_query.filter(TestCase.feature_id == feature_id)
    all_tcs = tc_query.all()

    linked_tc_ids = {t.tc_id for t in db.query(Traceability).all()}
    unlinked_tcs = [tc for tc in all_tcs if tc.tc_id not in linked_tc_ids]

    results = []
    for ac in unlinked_acs:
        if not unlinked_tcs:
            results.append({
                "ac_id": ac.ac_id,
                "feature_id": ac.feature_id,
                "ac_description": ac.description,
                "proposed_tc_id": None,
                "similarity_score": None,
                "status": "No link found",
                "detail": "No unlinked test cases available to compare against.",
            })
            continue

        scores = [(_similarity(ac.description, tc.description), tc) for tc in unlinked_tcs]
        scores.sort(key=lambda x: x[0], reverse=True)
        best_score, best_tc = scores[0]

        if best_score < SIMILARITY_THRESHOLD:
            results.append({
                "ac_id": ac.ac_id,
                "feature_id": ac.feature_id,
                "ac_description": ac.description,
                "proposed_tc_id": None,
                "similarity_score": round(best_score, 3),
                "status": "No link found",
                "detail": f"No confident match found (best similarity {best_score:.2f}).",
            })
        else:
            results.append({
                "ac_id": ac.ac_id,
                "feature_id": ac.feature_id,
                "ac_description": ac.description,
                "proposed_tc_id": best_tc.tc_id,
                "proposed_tc_description": best_tc.description,
                "similarity_score": round(best_score, 3),
                "status": "Implicit, inferred",
                "detail": f"AI inferred link to {best_tc.tc_id} (similarity {best_score:.2f}). Confirm before release.",
            })

    return results


def detect_stale_links(db: Session, feature_id: str = None):
    """RQ3: for every Acceptance Criterion with a RequirementHistory
    entry (its text changed) and an existing Traceability link, check
    whether the linked Test Case's description matches the OLD text
    more closely than the CURRENT (new) text. If so, flag as stale."""

    history_query = db.query(RequirementHistory)
    if feature_id:
        history_query = history_query.filter(RequirementHistory.feature_id == feature_id)
    histories = history_query.all()

    results = []
    for hist in histories:
        trace = db.query(Traceability).filter(
            Traceability.ac_id == hist.ac_id
        ).first()

        if not trace:
            continue  # no current link to check

        tc = db.query(TestCase).filter(TestCase.tc_id == trace.tc_id).first()
        ac = db.query(AcceptanceCriteria).filter(AcceptanceCriteria.ac_id == hist.ac_id).first()

        if not tc or not ac:
            continue

        sim_to_old = _similarity(tc.description, hist.old_text)
        sim_to_new = _similarity(tc.description, hist.new_text)

        is_stale = sim_to_old > sim_to_new

        results.append({
            "ac_id": hist.ac_id,
            "feature_id": hist.feature_id,
            "tc_id": tc.tc_id,
            "old_requirement_text": hist.old_text,
            "new_requirement_text": hist.new_text,
            "similarity_to_old": round(sim_to_old, 3),
            "similarity_to_new": round(sim_to_new, 3),
            "status": "Explicit, outdated" if is_stale else "Explicit, current",
            "detail": (
                f"Test case {tc.tc_id} matches the previous requirement wording more closely "
                f"({sim_to_old:.2f}) than the current wording ({sim_to_new:.2f}). Review needed."
                if is_stale else
                f"Test case {tc.tc_id} still matches the current requirement wording best "
                f"({sim_to_new:.2f} vs {sim_to_old:.2f} for the old wording). No action needed."
            ),
        })

    return results


def run_full_assessment(db: Session, feature_id: str = None):
    """Convenience wrapper returning both RQ2 and RQ3 results together."""
    return {
        "missing_link_inferences": infer_missing_links(db, feature_id),
        "stale_link_detections": detect_stale_links(db, feature_id),
    }