#!/usr/bin/env python3
"""
Stage 5: measure whether the AI component recovers real developer-created links.

Evaluation population (eval_population.csv), so that nothing is counted as an
error when the right answer is unknown:

  positive       a Kafka developer linked a test to this criterion, and that link
                 was held out of traceability.csv. ai.py should recover it.
                 -> correct proposal = TP; wrong or no proposal = FN
  true_negative  no developer ever touched a test for this criterion. The right
                 answer is "No link found".
                 -> no proposal = TN; any proposal = FP
  excluded       secondary criterion of a feature; true status unknown, not scored.

Three configurations are compared so the design choices can be reported with
evidence rather than asserted:
  A  pairwise TF-IDF fit on raw text      -- ai.py exactly as currently written
  B  corpus-wide TF-IDF fit on raw text   -- lets IDF actually discriminate
  C  corpus-wide fit, identifiers split   -- also fixes the tokenisation mismatch
"""
import csv, json, os, re
from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

D = "dataset"
THRESHOLDS = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60]
CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def rows(n):
    with open(os.path.join(D, n), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def normalise(t):
    t = t.replace("_", " ").replace(".", " ").replace("/", " ")
    return re.sub(r"\s+", " ", CAMEL.sub(" ", t)).lower().strip()


def sim_pairwise(at, tt):
    M = np.zeros((len(at), len(tt)))
    for i, a in enumerate(at):
        for j, t in enumerate(tt):
            if not a or not t:
                continue
            try:
                v = TfidfVectorizer(stop_words="english")
                m = v.fit_transform([a, t])
                M[i, j] = cosine_similarity(m[0:1], m[1:2])[0][0]
            except ValueError:
                pass
    return M


def sim_corpus(at, tt):
    v = TfidfVectorizer(stop_words="english", sublinear_tf=True)
    v.fit(at + tt)
    return cosine_similarity(v.transform(at), v.transform(tt))


def score(M, cand_acs, cand_tcs, gold, pos_ids, neg_ids, thr):
    tp = fn = fp = tn = 0
    for i, a in enumerate(cand_acs):
        if a not in pos_ids and a not in neg_ids:
            continue
        row = M[i]
        j = int(np.argmax(row)) if len(row) else -1
        proposed = j >= 0 and row[j] >= thr
        if a in pos_ids:
            if proposed and cand_tcs[j] in gold.get(a, set()):
                tp += 1
            else:
                fn += 1
        else:
            if proposed:
                fp += 1
            else:
                tn += 1
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    acc = (tp + tn) / max(tp + tn + fp + fn, 1)
    return dict(threshold=thr, tp=tp, fp=fp, fn=fn, tn=tn,
                precision=prec, recall=rec, f1=f1, accuracy=acc)


def main():
    acs = {r["ac_id"]: r["description"] for r in rows("acceptance_criteria.csv")}
    tcs = {r["tc_id"]: r["description"] for r in rows("test_cases.csv")}
    visible = {(r["ac_id"], r["tc_id"]) for r in rows("traceability.csv")}
    held = {(r["ac_id"], r["tc_id"]) for r in rows("ground_truth.csv") if r["held_out"] == "1"}
    popcls = {r["ac_id"]: r["ac_class"] for r in rows("eval_population.csv")}

    linked_acs = {a for a, _ in visible}
    linked_tcs = {t for _, t in visible}
    cand_acs = [a for a in acs if a not in linked_acs]
    cand_tcs = [t for t in tcs if t not in linked_tcs]
    tset = set(cand_tcs)
    cset = set(cand_acs)

    gold = defaultdict(set)
    for a, t in held:
        if a in cset and t in tset:
            gold[a].add(t)

    pos_ids = set(gold)
    neg_ids = {a for a in cand_acs if popcls.get(a) == "true_negative"}

    print(f"criteria                  {len(acs)}")
    print(f"test cases                {len(tcs)}")
    print(f"links visible to the app  {len(visible)}")
    print(f"links held out            {len(held)}")
    print(f"unlinked criteria         {len(cand_acs)}")
    print(f"unlinked test cases       {len(cand_tcs)}")
    print(f"\nscored population:")
    print(f"  positives (must recover) {len(pos_ids)}")
    print(f"  true negatives (must abstain) {len(neg_ids)}")
    print(f"  excluded, status unknown {len(cand_acs)-len(pos_ids)-len(neg_ids)}\n")

    at_raw = [acs[a] for a in cand_acs]
    tt_raw = [tcs[t] for t in cand_tcs]
    at_n = [normalise(x) for x in at_raw]
    tt_n = [normalise(x) for x in tt_raw]

    print("computing similarity matrices...")
    configs = [
        ("A  pairwise fit, raw text   (ai.py as written)", sim_pairwise(at_raw, tt_raw)),
        ("B  corpus fit, raw text", sim_corpus(at_raw, tt_raw)),
        ("C  corpus fit + identifiers split   (proposed)", sim_corpus(at_n, tt_n)),
    ]

    out = {}
    for label, M in configs:
        print(f"\n{'='*78}\n  {label}\n{'='*78}")
        print(f"  {'thr':>5} {'TP':>4} {'FP':>4} {'FN':>4} {'TN':>4} "
              f"{'precision':>10} {'recall':>8} {'F1':>7} {'acc':>7}")
        rs = []
        for thr in THRESHOLDS:
            r = score(M, cand_acs, cand_tcs, gold, pos_ids, neg_ids, thr)
            rs.append(r)
            print(f"  {thr:>5.2f} {r['tp']:>4} {r['fp']:>4} {r['fn']:>4} {r['tn']:>4} "
                  f"{r['precision']:>10.3f} {r['recall']:>8.3f} {r['f1']:>7.3f} {r['accuracy']:>7.3f}")
        b = max(rs, key=lambda r: r["f1"])
        print(f"  --> best F1 {b['f1']:.3f} at threshold {b['threshold']:.2f}  "
              f"(P={b['precision']:.3f}  R={b['recall']:.3f}  acc={b['accuracy']:.3f})")
        out[label] = rs

    with open("evaluation_results.json", "w") as fh:
        json.dump(out, fh, indent=2)
    print("\nwrote evaluation_results.json")


if __name__ == "__main__":
    main()
