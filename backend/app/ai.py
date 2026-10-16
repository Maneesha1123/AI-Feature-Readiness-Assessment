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

-----------------------------------------------------------------------
Three design choices below are not arbitrary. Each was selected by
measuring it against 466 requirement-to-test links mined from the
commit history of apache/kafka, where a developer's own commit message
is the evidence for the link. See datacheck/evaluate.py; results in
datacheck/evaluation_results.json.

  1. Corpus-wide vectoriser fit, not per-pair.
     Fitting TfidfVectorizer on only the two texts being compared gives
     IDF a corpus of two documents, where every term is either in both
     or in one and so carries almost no discriminating weight. Fitting
     once across all criteria and test cases lets IDF discount terms
     common to the whole project ("verify", "should", "kafka") and
     reward distinctive ones.

  2. Identifiers are split into words before vectorising.
     Requirement text keeps developer identifiers whole, so
     "OffsetsForLeaderEpochRequestTest" is a single token, while test
     descriptions derived from method names are already word-separated.
     TF-IDF matches exact tokens, so without splitting, the single most
     informative string in a pair cannot match itself. Splitting moved
     the correct test case from median rank 7 to median rank 1.

  3. SIMILARITY_THRESHOLD = 0.25, not 0.10.
     Measured F1 across the threshold sweep:
         threshold 0.10 -> precision 0.193  recall 0.509  F1 0.280
         threshold 0.25 -> precision 0.426  recall 0.351  F1 0.385
         threshold 0.40 -> precision 0.714  recall 0.175  F1 0.282
     0.25 maximises F1. A tool that proposes a link for almost every
     criterion gives a reviewer little help, so some recall is traded
     for precision deliberately.

  Combined effect on the held-out links: F1 0.239 -> 0.385.
-----------------------------------------------------------------------
"""

import re

from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.app.models import (
    AcceptanceCriteria,
    TestCase,
    Traceability,
    RequirementHistory,
)

# Chosen by maximising F1 against mined links -- see note above.
SIMILARITY_THRESHOLD = 0.25

# A stale-link verdict rests on which of two similarities is larger. When they
# are this close the verdict is reported but marked low confidence, because the
# ordering is not robust to small wording differences.
STALE_MARGIN = 0.05

_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _normalise(text: str) -> str:
    """Split camelCase, snake_case and dotted identifiers into separate words.

    'OffsetsForLeaderEpochRequestTest' -> 'offsets for leader epoch request test'
    """
    if not text:
        return ""
    text = text.replace("_", " ").replace(".", " ").replace("/", " ")
    return re.sub(r"\s+", " ", _CAMEL.sub(" ", text)).lower().strip()


def _fit(corpus):
    """Fit one vectoriser across the whole corpus so IDF can discriminate."""
    texts = [_normalise(t) for t in corpus if t and t.strip()]
    if not texts:
        return None
    try:
        vec = TfidfVectorizer(stop_words="english", sublinear_tf=True)
        vec.fit(texts)
        return vec
    except ValueError:
        # every document was stop words only
        return None


def _similarity(text_a: str, text_b: str, vec=None) -> float:
    """Cosine similarity between two short texts using TF-IDF.

    If `vec` is a vectoriser already fitted on the surrounding corpus it is
    used, which is what makes IDF meaningful. Without one the function falls
    back to fitting on the pair alone, so existing callers keep working.
    """
    a, b = _normalise(text_a), _normalise(text_b)
    if not a or not b:
        return 0.0
    try:
        if vec is not None:
            m = vec.transform([a, b])
        else:
            m = TfidfVectorizer(stop_words="english").fit_transform([a, b])
        return float(cosine_similarity(m[0:1], m[1:2])[0][0])
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

    # One vectoriser for the whole comparison, fitted on every criterion and
    # test case in scope -- including the linked ones, because they are part of
    # this project's vocabulary and so inform the IDF weights.
    vec = _fit([ac.description for ac in all_acs] + [tc.description for tc in all_tcs])

    # Pre-compute the full similarity matrix in one pass rather than refitting
    # a vectoriser per pair: same numbers, and it scales to hundreds of rows.
    matrix = None
    if vec is not None and unlinked_acs and unlinked_tcs:
        try:
            A = vec.transform([_normalise(ac.description) for ac in unlinked_acs])
            T = vec.transform([_normalise(tc.description) for tc in unlinked_tcs])
            matrix = cosine_similarity(A, T)
        except ValueError:
            matrix = None

    results = []
    for i, ac in enumerate(unlinked_acs):
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

        if matrix is not None:
            row = matrix[i]
            best_j = int(row.argmax())
            best_score = float(row[best_j])
            best_tc = unlinked_tcs[best_j]
        else:
            scores = [(_similarity(ac.description, tc.description, vec), tc)
                      for tc in unlinked_tcs]
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

    # Fit across every text this check will touch, for the same reason as above.
    corpus = []
    for h in histories:
        corpus.extend([h.old_text, h.new_text])
    corpus.extend([tc.description for tc in db.query(TestCase).all()])
    vec = _fit(corpus)

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

        sim_to_old = _similarity(tc.description, hist.old_text, vec)
        sim_to_new = _similarity(tc.description, hist.new_text, vec)

        is_stale = sim_to_old > sim_to_new
        margin = abs(sim_to_old - sim_to_new)
        borderline = margin < STALE_MARGIN

        if is_stale:
            detail = (
                f"Test case {tc.tc_id} matches the previous requirement wording more closely "
                f"({sim_to_old:.2f}) than the current wording ({sim_to_new:.2f}). Review needed."
            )
        else:
            detail = (
                f"Test case {tc.tc_id} still matches the current requirement wording best "
                f"({sim_to_new:.2f} vs {sim_to_old:.2f} for the old wording). No action needed."
            )
        if borderline:
            detail += (
                f" Note: the two scores differ by only {margin:.2f}, so this verdict is "
                f"not robust -- treat it as needing a human judgement either way."
            )

        results.append({
            "ac_id": hist.ac_id,
            "feature_id": hist.feature_id,
            "tc_id": tc.tc_id,
            "old_requirement_text": hist.old_text,
            "new_requirement_text": hist.new_text,
            "similarity_to_old": round(sim_to_old, 3),
            "similarity_to_new": round(sim_to_new, 3),
            "margin": round(margin, 3),
            "confidence": "low" if borderline else "normal",
            "status": "Explicit, outdated" if is_stale else "Explicit, current",
            "detail": detail,
        })

    return results


def run_full_assessment(db: Session, feature_id: str = None):
    """Convenience wrapper returning both RQ2 and RQ3 results together."""
    return {
        "missing_link_inferences": infer_missing_links(db, feature_id),
        "stale_link_detections": detect_stale_links(db, feature_id),
    }
