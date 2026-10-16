#!/usr/bin/env python3
"""
Diagnostic: is the weak F1 a limit of the technique, or a preprocessing bug?

Two suspicions.

(1) Tokenisation mismatch. Acceptance-criteria text keeps developer identifiers
    whole ("OffsetsForLeaderEpochRequestTest" is one token) while test
    descriptions were already camelCase-split into words ("offsets for leader
    epoch request"). TF-IDF matches on exact tokens, so the single most
    informative string in the pair cannot match itself.

(2) No "no match" option. ai.py proposes its best candidate for every unlinked
    criterion. Most unlinked criteria here have no recoverable link at all, so
    each one is a guaranteed false positive however good the ranking is.

Reports recall@k to separate "the technique has no signal" from "the technique
has signal but ranks badly" or "the ranking is fine, the cutoff rule is wrong".
"""
import csv, os, re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

D = "dataset"
CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def rows(n):
    with open(os.path.join(D, n), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def normalise(t):
    """Split camelCase/snake_case identifiers and dotted paths into words."""
    t = t.replace("_", " ").replace(".", " ").replace("/", " ")
    t = CAMEL.sub(" ", t)
    return re.sub(r"\s+", " ", t).lower().strip()


def main():
    acs = {r["ac_id"]: r["description"] for r in rows("acceptance_criteria.csv")}
    tcs = {r["tc_id"]: r["description"] for r in rows("test_cases.csv")}
    visible = {(r["ac_id"], r["tc_id"]) for r in rows("traceability.csv")}
    truth = rows("ground_truth.csv")
    held = {(r["ac_id"], r["tc_id"]) for r in truth if r["held_out"] == "1"}

    linked_acs = {a for a, _ in visible}
    linked_tcs = {t for _, t in visible}
    cand_acs = [a for a in acs if a not in linked_acs]
    cand_tcs = [t for t in tcs if t not in linked_tcs]
    tset = set(cand_tcs)

    # criteria whose true partner is actually in the candidate pool
    gold = {}
    for a, t in held:
        if a in set(cand_acs) and t in tset:
            gold.setdefault(a, set()).add(t)

    print(f"unlinked criteria                {len(cand_acs)}")
    print(f"unlinked test cases              {len(cand_tcs)}")
    print(f"criteria with a recoverable link {len(gold)}")
    print(f"criteria with NO recoverable link{len(cand_acs)-len(gold):>5}"
          f"   <- every proposal for these is a false positive by construction\n")

    for label, norm in (("raw text (as ai.py sees it)", False),
                        ("identifiers split into words", True)):
        at = [normalise(acs[a]) if norm else acs[a] for a in cand_acs]
        tt = [normalise(tcs[t]) if norm else tcs[t] for t in cand_tcs]
        v = TfidfVectorizer(stop_words="english", sublinear_tf=True)
        v.fit(at + tt)
        M = cosine_similarity(v.transform(at), v.transform(tt))

        print(f"{'='*70}\n  {label}\n{'='*70}")
        ks = [1, 3, 5, 10]
        hits = {k: 0 for k in ks}
        ranks, topsims = [], []
        for i, a in enumerate(cand_acs):
            if a not in gold:
                continue
            order = np.argsort(-M[i])
            names = [cand_tcs[j] for j in order]
            pos = next((p for p, n in enumerate(names, 1) if n in gold[a]), None)
            if pos:
                ranks.append(pos)
                for k in ks:
                    if pos <= k:
                        hits[k] += 1
            topsims.append(M[i][order[0]])

        n = len(gold)
        for k in ks:
            print(f"  recall@{k:<3} {hits[k]:>4}/{n}   {hits[k]/n:>6.1%}")
        if ranks:
            print(f"  median rank of the true test case: {int(np.median(ranks))}")
        print(f"  mean top-1 similarity: {np.mean(topsims):.3f}\n")


if __name__ == "__main__":
    main()
