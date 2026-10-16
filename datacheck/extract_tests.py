#!/usr/bin/env python3
"""
Stage 2: turn test files into readable test-case descriptions.

A test file path alone is thin input for TF-IDF. Test *method names* are not:
Java and Scala convention makes them descriptive sentences in camelCase, e.g.
  shouldNotAllowOffsetCommitWhenGroupIsRebalancing
  testDefaultsToLocalhostWhenNoHostnameGiven
Splitting those into words yields authentic developer-written prose describing
exactly what is verified -- which is what we want to match requirement text
against. ScalaTest's test("...") form gives literal prose directly.

Output: test_descriptions.json   { "path": {"methods": [...], "text": "..."} }
"""
import json, re, subprocess, sys, time

# @Test (optionally with args/newlines) then ... methodName(
JAVA_TEST = re.compile(
    r"@Test\b[^\n]*(?:\n\s*@[^\n]*)*\s*(?:public|private|protected)?\s*"
    r"(?:<[^>]+>\s*)?[\w.<>\[\]]+\s+(\w+)\s*\(",
    re.MULTILINE,
)
SCALA_ANNOT = re.compile(r"@Test\b[^\n]*(?:\n\s*@[^\n]*)*\s*def\s+(\w+)\s*[(:]", re.MULTILINE)
SCALA_FUNSUITE = re.compile(r"""\btest\s*\(\s*["']([^"']{6,160})["']""")
PY_TEST = re.compile(r"^\s*def\s+(test_\w+)\s*\(", re.MULTILINE)

CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def words(name: str) -> str:
    """shouldNotAllowOffsetCommit -> 'should not allow offset commit'"""
    name = re.sub(r"^(test|should|it)[_]?", "", name)
    name = name.replace("_", " ")
    return CAMEL.sub(" ", name).lower().strip()


def class_name(path: str) -> str:
    base = path.rsplit("/", 1)[-1]
    base = re.sub(r"\.(java|scala|py|kt)$", "", base)
    base = re.sub(r"(Test|Tests|IT|_test)$", "", base)
    return words(base)


def describe(path: str, src: str) -> dict:
    methods = []
    if path.endswith(".java") or path.endswith(".kt"):
        methods = JAVA_TEST.findall(src)
    elif path.endswith(".scala"):
        methods = SCALA_ANNOT.findall(src)
        lits = SCALA_FUNSUITE.findall(src)
        if lits:
            methods = methods + lits
    elif path.endswith(".py"):
        methods = PY_TEST.findall(src)

    seen, clean = set(), []
    for m in methods:
        w = m if " " in m else words(m)
        w = re.sub(r"\s+", " ", w).strip()
        if len(w) > 3 and w not in seen:
            seen.add(w)
            clean.append(w)

    subject = class_name(path)
    # The description a human would read: what is under test, then the cases.
    text = f"Verify {subject}. " + "; ".join(clean[:12]) if clean else f"Verify {subject}."
    return {"methods": clean[:40], "n_methods": len(clean), "subject": subject,
            "text": re.sub(r"\s+", " ", text).strip()[:1200]}


def main():
    d = json.load(open("mined_links.json"))
    need = {}
    for r in d["sample_linked"]:
        for path, sha in r["tests"].items():
            need.setdefault(path, sha)

    print(f"fetching {len(need)} test files from apache/kafka ...")
    out, fail = {}, []
    t0 = time.time()
    for i, (path, sha) in enumerate(need.items(), 1):
        p = subprocess.run(["git", "-C", "kafka", "cat-file", "-p", f"{sha}:{path}"],
                           capture_output=True, text=True, timeout=180)
        if p.returncode != 0 or not p.stdout.strip():
            fail.append(path)
            continue
        out[path] = describe(path, p.stdout)
        if i % 50 == 0:
            print(f"  {i}/{len(need)}  ({time.time()-t0:.0f}s)")

    with open("test_descriptions.json", "w") as f:
        json.dump(out, f, indent=2)

    withm = [v for v in out.values() if v["n_methods"] > 0]
    print(f"\nfetched           {len(out)}/{len(need)}   (failed {len(fail)})")
    print(f"with method names {len(withm)}  ({100*len(withm)//max(len(out),1)}%)")
    print(f"mean methods/file {sum(v['n_methods'] for v in withm)/max(len(withm),1):.1f}")
    print("\nexamples:")
    for path, v in list(out.items())[:4]:
        if v["n_methods"]:
            print(f"\n  {path.rsplit('/',1)[-1]}")
            print(f"    {v['text'][:230]}")
    print("\nwrote test_descriptions.json")


if __name__ == "__main__":
    main()
