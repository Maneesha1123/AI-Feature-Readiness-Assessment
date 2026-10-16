#!/usr/bin/env python3
"""
Stage 1: mine real requirement -> test-case links from Apache git history.

Apache projects use Jira for requirements and git for code, and Apache
convention requires every commit message to cite its Jira key. So a commit
that cites KAFKA-1234 and also modifies a file under src/test/ is
developer-created evidence that those tests verify that requirement.

Output: mined_links.json
  - linked:   issues whose commits touched test files  (RQ2 ground-truth positive)
  - unlinked: issues whose commits touched only production code (RQ2 positive case
              to detect: a real requirement with no test linked to it)

No manual annotation is involved at any point.
"""
import re, subprocess, json, random, sys
from collections import defaultdict

REPO = sys.argv[1] if len(sys.argv) > 1 else "kafka"
PREFIX = {"kafka": "KAFKA", "commons-lang": "LANG"}[REPO]
KEYPAT = re.compile(rf"\b{PREFIX}-(\d+)\b")

SAMPLE_LINKED = 300
SAMPLE_UNLINKED = 150
SEED = 42

TEST_PAT = re.compile(r"(^|/)src/test/|(^|/)tests?/|[Tt]est[s]?\.(java|scala|py|kt)$|_test\.(java|py|go)$")
CODE_PAT = re.compile(r"\.(java|scala|py|kt|go)$")


def iter_commits(repo):
    out = subprocess.run(
        ["git", "-C", repo, "log", "--no-merges", "--name-only",
         "--pretty=format:@@@%H%x01%at%x01%s%x01%b%x02"],
        capture_output=True, text=True, timeout=900,
    ).stdout
    for block in out.split("@@@")[1:]:
        if "\x02" not in block:
            continue
        head, files = block.split("\x02", 1)
        parts = head.split("\x01")
        if len(parts) < 4:
            continue
        sha, ts, subj, body = parts[0], parts[1], parts[2], parts[3]
        yield sha, int(ts), subj, body, [f for f in files.strip().split("\n") if f.strip()]


def main():
    issues = defaultdict(lambda: {
        "tests": {}, "code": set(), "subjects": [], "first_ts": None, "commits": 0
    })

    n = 0
    for sha, ts, subj, body, files in iter_commits(REPO):
        n += 1
        keys = set(KEYPAT.findall(subj + "\n" + body))
        if not keys:
            continue
        tests = [f for f in files if TEST_PAT.search(f)]
        code = [f for f in files if CODE_PAT.search(f) and not TEST_PAT.search(f)]
        for k in keys:
            e = issues[k]
            e["commits"] += 1
            for t in tests:
                e["tests"].setdefault(t, sha)   # remember a sha that contained it
            e["code"].update(code)
            if subj not in e["subjects"]:
                e["subjects"].append(subj)
            if e["first_ts"] is None or ts < e["first_ts"]:
                e["first_ts"] = ts

    linked, unlinked = {}, {}
    for k, v in issues.items():
        rec = {
            "key": f"{PREFIX}-{k}",
            "tests": v["tests"],
            "code": sorted(v["code"])[:8],
            "subjects": v["subjects"][:3],
            "commits": v["commits"],
            "first_ts": v["first_ts"],
        }
        if v["tests"]:
            linked[k] = rec
        elif v["code"]:
            unlinked[k] = rec

    random.seed(SEED)
    # Prefer issues with a modest number of test files: cleaner, more
    # interpretable links than a sweeping refactor that touched 40 test files.
    lk = [k for k in linked if 1 <= len(linked[k]["tests"]) <= 3]
    uk = list(unlinked)
    random.shuffle(lk); random.shuffle(uk)

    out = {
        "repo": f"apache/{REPO}",
        "jira_prefix": PREFIX,
        "jira_base": "https://issues.apache.org/jira",
        "stats": {
            "commits_analysed": n,
            "issues_referenced": len(issues),
            "issues_linked_to_tests": len(linked),
            "issues_code_only": len(unlinked),
            "linked_with_1_to_3_tests": len(lk),
        },
        "sample_linked": [linked[k] for k in lk[:SAMPLE_LINKED]],
        "sample_unlinked": [unlinked[k] for k in uk[:SAMPLE_UNLINKED]],
    }

    with open("mined_links.json", "w") as f:
        json.dump(out, f, indent=2)

    s = out["stats"]
    print(f"repo                        apache/{REPO}")
    print(f"commits analysed            {s['commits_analysed']:>8,}")
    print(f"Jira issues referenced      {s['issues_referenced']:>8,}")
    print(f"  linked to >=1 test file   {s['issues_linked_to_tests']:>8,}")
    print(f"  code only, no test        {s['issues_code_only']:>8,}")
    print(f"  linked with 1-3 tests     {s['linked_with_1_to_3_tests']:>8,}  <- sampling pool")
    print(f"\nsampled {len(out['sample_linked'])} linked + {len(out['sample_unlinked'])} unlinked")
    print(f"unique test files to fetch  {len({t for r in out['sample_linked'] for t in r['tests']}):>8,}")
    print("\nwrote mined_links.json")


if __name__ == "__main__":
    main()
