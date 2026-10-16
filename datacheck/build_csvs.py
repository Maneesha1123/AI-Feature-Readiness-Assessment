#!/usr/bin/env python3
"""
Stage 4: assemble the mined evidence into the prototype's existing 6-CSV schema.

Two modes:

  python build_csvs.py --preview
      Uses the Jira keys and commit subjects already mined from git. Needs no
      network. Gives a working dataset at full scale immediately, but
      acceptance-criteria text is only the one-line commit subject and there is
      no requirement-change history, so RQ3 stays empty.

  python build_csvs.py
      Uses jira_issues.json from fetch_jira.py. Full issue descriptions as
      acceptance criteria, and real recorded requirement edits for RQ3.

Writes into dataset/:
    features.csv  acceptance_criteria.csv  test_cases.csv
    traceability.csv  requirement_history.csv  deployment.csv
  plus
    ground_truth.csv   -- the reference set for precision/recall (not loaded by the app)

Evaluation design
-----------------
Every link in traceability.csv came from a developer's own commit, so the full
set of mined links is the reference set. A random HOLDOUT_FRAC of them is
removed from traceability.csv before the prototype sees it; ai.py then has to
recover them. ground_truth.csv records which links are real and which were
held out, so precision and recall are measured against real links rather than
against anything annotated by hand.
"""
import csv, hashlib, json, os, random, re, sys
from collections import defaultdict

HOLDOUT_FRAC = 0.30
SEED = 7
OUTDIR = "dataset"

PREVIEW = "--preview" in sys.argv


# ---------- text cleaning ----------------------------------------------------

JIRA_NOISE = [
    (re.compile(r"\{code(:[^}]*)?\}.*?\{code\}", re.S), " "),
    (re.compile(r"\{noformat\}.*?\{noformat\}", re.S), " "),
    (re.compile(r"\{quote\}.*?\{quote\}", re.S), " "),
    (re.compile(r"\{\{(.*?)\}\}", re.S), r"\1"),
    (re.compile(r"https?://\S+"), " "),
    (re.compile(r"\[~[^\]]+\]"), " "),                 # user mentions
    (re.compile(r"\[([^|\]]+)\|[^\]]*\]"), r"\1"),     # [text|link]
    (re.compile(r"^\s*h[1-6]\.\s*", re.M), ""),
    (re.compile(r"[*_+\-]{2,}"), " "),
    (re.compile(r"\|"), " "),
    (re.compile(r"\s+"), " "),
]

KEYPAT = re.compile(r"\b[A-Z][A-Z0-9_]+-\d+\b")


def clean(t: str, limit: int = 700) -> str:
    if not t:
        return ""
    for pat, rep in JIRA_NOISE:
        t = pat.sub(rep, t)
    t = KEYPAT.sub(" ", t)           # don't let the issue key itself drive similarity
    t = t.strip(" .;:-")
    if len(t) > limit:
        cut = t[:limit]
        t = cut[: cut.rfind(" ")] if " " in cut else cut
    return t.strip()


def subject_to_requirement(subj: str) -> str:
    """'KAFKA-123: Fix flaky foo test (#456)' -> 'Fix flaky foo test'"""
    s = KEYPAT.sub("", subj)
    s = re.sub(r"\(#\d+\)", "", s)
    # repeatedly strip conventional prefixes and leftover punctuation, in any order
    for _ in range(4):
        s = re.sub(r"^[\s:;,./\-\[\]()|]+", "", s)
        # only pure tags -- "Fix"/"Add"/"Remove" are part of the requirement itself
        s = re.sub(r"^(MINOR|HOTFIX|TRIVIAL|WIP)\b\s*[:\-]?\s*", "", s, flags=re.I)
    return clean(s, 400)


def split_criteria(desc: str, summary: str):
    """
    A Jira description often enumerates several conditions. Each becomes its
    own acceptance criterion; otherwise the whole description is one.
    """
    if not desc:
        return [clean(summary, 400)] if summary else []
    raw = re.split(r"\n\s*(?:[*\-#]\s+|\d+[.)]\s+)", "\n" + desc)
    parts = [clean(p, 450) for p in raw]
    parts = [p for p in parts if len(p.split()) >= 6]
    if len(parts) >= 2:
        return parts[:6]
    whole = clean(desc, 700)
    return [whole] if len(whole.split()) >= 5 else ([clean(summary, 400)] if summary else [])


def anon(s: str) -> str:
    """Opaque, stable, non-reversible stand-in for a reporter id."""
    if not s:
        return "PO-unknown"
    return "PO-" + hashlib.sha256(s.encode()).hexdigest()[:8]


def sprint_of(created: str, fallback_ts) -> str:
    if created and len(created) >= 7:
        y, m = created[:4], int(created[5:7])
        return f"{y}-Q{(m-1)//3 + 1}"
    if fallback_ts:
        import datetime
        d = datetime.datetime.utcfromtimestamp(fallback_ts)
        return f"{d.year}-Q{(d.month-1)//3 + 1}"
    return "unknown"


def deployment_of(iss):
    """Map Jira resolution state onto the prototype's environment/status pair."""
    if not iss:
        return ("development", "pending")
    res, status = iss.get("resolution"), (iss.get("status") or "")
    fv = iss.get("fix_versions") or []
    if res in ("Fixed", "Done", "Delivered", "Implemented") and fv:
        return ("production", "ready")
    if res in ("Fixed", "Done", "Delivered", "Implemented"):
        return ("staging", "ready")
    if status.lower() in ("resolved", "closed"):
        return ("staging", "ready")
    return ("development", "pending")


# ---------- assembly ---------------------------------------------------------

def main():
    if not os.path.exists("mined_links.json"):
        sys.exit("mined_links.json not found. Run: python mine_links.py kafka")
    mined = json.load(open("mined_links.json", encoding="utf-8"))
    tdesc = json.load(open("test_descriptions.json", encoding="utf-8")) \
        if os.path.exists("test_descriptions.json") else {}

    jira = {}
    if not PREVIEW:
        if not os.path.exists("jira_issues.json"):
            sys.exit("jira_issues.json not found.\n"
                     "Either run fetch_jira.py on your laptop first,\n"
                     "or run:  python build_csvs.py --preview")
        jira = {k: v for k, v in json.load(open("jira_issues.json", encoding="utf-8")).items()
                if "error" not in v}

    os.makedirs(OUTDIR, exist_ok=True)
    random.seed(SEED)

    features, acs, tcs, trace, hist, deploy, truth, pop = [], [], [], [], [], [], [], []
    tc_by_path = {}          # one test-case row per distinct test file
    fid = acid = tcid = 0
    n_no_text = 0

    records = [(r, True) for r in mined["sample_linked"]] + \
              [(r, False) for r in mined["sample_unlinked"]]

    for rec, is_linked in records:
        key = rec["key"]
        iss = jira.get(key)
        if not PREVIEW and iss is None:
            continue

        summary = (iss or {}).get("summary") or subject_to_requirement(rec["subjects"][0] if rec["subjects"] else "")
        if PREVIEW:
            criteria = [subject_to_requirement(s) for s in rec["subjects"][:3]]
            criteria = [c for c in criteria if len(c.split()) >= 4] or ([clean(summary, 400)] if summary else [])
        else:
            criteria = split_criteria(iss.get("description", ""), summary)

        if not criteria or not summary:
            n_no_text += 1
            continue

        fid += 1
        f = f"F{fid:04d}"
        features.append({
            "feature_id": f,
            "feature_name": clean(summary, 160) or key,
            "sprint": sprint_of((iss or {}).get("created"), rec.get("first_ts")),
            "product_owner": anon((iss or {}).get("reporter_key") or key),
            "jira_key": key,
        })

        env, st = deployment_of(iss)
        deploy.append({"feature_id": f, "environment": env, "status": st})

        # --- acceptance criteria, and version bump if the text was later edited
        changes = (iss or {}).get("text_changes") or []
        ac_ids = []
        for i, c in enumerate(criteria):
            acid += 1
            a = f"AC-{acid:04d}"
            ac_ids.append(a)
            acs.append({
                "ac_id": a, "feature_id": f,
                "description": c,
                "version": 2 if (changes and i == 0) else 1,
            })

        # --- requirement history: real recorded edits, first criterion only
        if changes:
            ch = changes[-1]           # most recent edit
            o, nw = clean(ch["old_text"], 700), clean(ch["new_text"], 700)
            if o and nw and o != nw and len(o.split()) >= 5 and len(nw.split()) >= 5:
                hist.append({"feature_id": f, "ac_id": ac_ids[0],
                             "old_text": o, "new_text": nw})

        # --- evaluation population (see eval_population.csv note below)
        # Only the first criterion of each feature carries a mined link, so it
        # is the only one whose correct answer is known. Secondary criteria are
        # excluded from scoring rather than silently counted as errors.
        for i, a in enumerate(ac_ids):
            if i > 0:
                cls = "excluded_unknown"
            elif is_linked:
                cls = "positive"          # a real test exists; may be held out
            else:
                cls = "true_negative"     # developer never touched a test for this
            pop.append({"ac_id": a, "feature_id": f, "jira_key": key, "ac_class": cls})

        # --- test cases from the files the developer touched alongside the fix
        if is_linked:
            for path in rec["tests"]:
                if path not in tc_by_path:
                    d = tdesc.get(path)
                    if not d or not d.get("text"):
                        continue
                    tcid += 1
                    t = f"TC-{tcid:04d}"
                    tc_by_path[path] = t
                    tcs.append({
                        "tc_id": t, "feature_id": f,
                        "description": d["text"],
                        "result": "pass",
                        "test_file": path,
                    })
                t = tc_by_path[path]
                a = ac_ids[0]
                held = random.random() < HOLDOUT_FRAC
                truth.append({"ac_id": a, "tc_id": t, "feature_id": f,
                              "is_true_link": 1, "held_out": int(held),
                              "evidence": f"commit in {mined['repo']} citing {key}"})
                if not held:
                    trace.append({"feature_id": f, "ac_id": a,
                                  "tc_id": t, "status": "Linked"})

    def write(name, rows, cols):
        with open(os.path.join(OUTDIR, name), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)

    write("features.csv", features, ["feature_id", "feature_name", "sprint", "product_owner"])
    write("acceptance_criteria.csv", acs, ["ac_id", "feature_id", "description", "version"])
    write("test_cases.csv", tcs, ["tc_id", "feature_id", "description", "result"])
    write("traceability.csv", trace, ["feature_id", "ac_id", "tc_id", "status"])
    write("requirement_history.csv", hist, ["feature_id", "ac_id", "old_text", "new_text"])
    write("deployment.csv", deploy, ["feature_id", "environment", "status"])
    write("ground_truth.csv", truth, ["ac_id", "tc_id", "feature_id", "is_true_link", "held_out", "evidence"])
    # Which criteria may legitimately be scored, and what the right answer is:
    #   positive         -- a developer did link a test; if held out, ai.py should recover it
    #   true_negative    -- no test was ever linked; ai.py should report no link found
    #   excluded_unknown -- secondary criterion, true status unknown, not scored
    write("eval_population.csv", pop, ["ac_id", "feature_id", "jira_key", "ac_class"])
    # provenance sidecars, not loaded by the app
    write("features_provenance.csv", features, ["feature_id", "jira_key", "feature_name"])
    write("test_cases_provenance.csv", tcs, ["tc_id", "test_file", "feature_id"])

    held = sum(t["held_out"] for t in truth)
    print(f"mode                 {'PREVIEW (commit subjects)' if PREVIEW else 'FULL (Jira text + history)'}")
    print(f"source               {mined['repo']}")
    print(f"{'-'*52}")
    print(f"features             {len(features):>6}")
    print(f"acceptance criteria  {len(acs):>6}")
    print(f"test cases           {len(tcs):>6}")
    print(f"traceability links   {len(trace):>6}   (visible to the prototype)")
    print(f"ground-truth links   {len(truth):>6}")
    print(f"  held out for RQ2   {held:>6}   <- ai.py must recover these")
    print(f"requirement history  {len(hist):>6}   <- RQ3 cases")
    print(f"skipped, no text     {n_no_text:>6}")
    print(f"{'-'*52}")
    print(f"written to {OUTDIR}/")


if __name__ == "__main__":
    main()
