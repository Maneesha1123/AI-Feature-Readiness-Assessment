#!/usr/bin/env python3
"""
Data availability check (Reviewer 2's request).

Question: in a real project that uses Jira for requirements and GitHub for code,
how often can a requirement (Jira issue) be linked to the test cases that
verify it, using only developer-created evidence (commit messages + changed files)?

No manual annotation. No synthetic data.
"""
import re, subprocess, sys, json
from collections import defaultdict

REPOS = {
    "commons-lang": r"\bLANG-(\d+)\b",
    "kafka":        r"\bKAFKA-(\d+)\b",
}

TEST_PAT = re.compile(r"(^|/)(src/test/|tests?/|.*[Tt]est[s]?\.(java|py|scala|kt)$|.*_test\.(java|py|go)$)")
CODE_PAT = re.compile(r"\.(java|scala|py|kt|go)$")


def commits_with_files(repo):
    """Yield (jira_keys, [files]) per commit."""
    out = subprocess.run(
        ["git", "-C", repo, "log", "--no-merges", "--name-only",
         "--pretty=format:@@@%H%n%s%n%b%n---FILES---"],
        capture_output=True, text=True, timeout=600,
    ).stdout
    for block in out.split("@@@")[1:]:
        if "---FILES---" not in block:
            continue
        msg, files = block.split("---FILES---", 1)
        yield msg, [f for f in files.strip().split("\n") if f.strip()]


def analyse(repo, keypat):
    pat = re.compile(keypat)
    total = 0
    with_key = 0
    key_and_test = 0
    key_and_code_no_test = 0
    issues = defaultdict(lambda: {"tests": set(), "code": set(), "commits": 0})

    for msg, files in commits_with_files(repo):
        total += 1
        keys = set(pat.findall(msg))
        if not keys:
            continue
        with_key += 1
        tests = [f for f in files if TEST_PAT.search(f)]
        code = [f for f in files if CODE_PAT.search(f) and not TEST_PAT.search(f)]
        if tests:
            key_and_test += 1
        elif code:
            key_and_code_no_test += 1
        for k in keys:
            issues[k]["tests"].update(tests)
            issues[k]["code"].update(code)
            issues[k]["commits"] += 1

    linked = {k: v for k, v in issues.items() if v["tests"]}
    unlinked = {k: v for k, v in issues.items() if not v["tests"] and v["code"]}

    return {
        "repo": repo,
        "commits_total": total,
        "commits_with_jira_key": with_key,
        "pct_commits_with_key": round(100 * with_key / total, 1) if total else 0,
        "commits_key_and_test": key_and_test,
        "commits_key_code_no_test": key_and_code_no_test,
        "unique_issues_referenced": len(issues),
        "issues_with_test_link": len(linked),
        "issues_code_but_no_test": len(unlinked),
        "pct_issues_with_test_link": round(100 * len(linked) / len(issues), 1) if issues else 0,
        "_linked": linked,
        "_unlinked": unlinked,
    }


if __name__ == "__main__":
    results = []
    for repo, pat in REPOS.items():
        r = analyse(repo, pat)
        results.append(r)
        print(f"\n{'='*62}\n  apache/{repo}\n{'='*62}")
        print(f"  commits analysed                 {r['commits_total']:>8,}")
        print(f"  commits citing a Jira key        {r['commits_with_jira_key']:>8,}   ({r['pct_commits_with_key']}%)")
        print(f"  ...of those, touching a test     {r['commits_key_and_test']:>8,}")
        print(f"  ...touching code but no test     {r['commits_key_code_no_test']:>8,}")
        print(f"  ---")
        print(f"  unique Jira issues referenced    {r['unique_issues_referenced']:>8,}")
        print(f"  issues WITH a test link  (RQ2 +) {r['issues_with_test_link']:>8,}   ({r['pct_issues_with_test_link']}%)")
        print(f"  issues with code, NO test (RQ2 ?){r['issues_code_but_no_test']:>8,}")

        ex = list(r["_linked"].items())[:3]
        if ex:
            print(f"\n  examples of real AC->TC links:")
            for k, v in ex:
                t = sorted(v["tests"])[0]
                print(f"    {repo.split('-')[0].upper()}-{k}  ->  {t[:70]}")

    with open("availability_results.json", "w") as f:
        json.dump([{k: v for k, v in r.items() if not k.startswith("_")} for r in results], f, indent=2)
    print("\nwrote availability_results.json")
