#!/usr/bin/env python3
"""
Stage 3: fetch requirement text and change history from Apache's public Jira.

RUN THIS ON YOUR OWN LAPTOP -- the cloud sandbox cannot reach
issues.apache.org, but your machine can.

    python fetch_jira.py

It reads mined_links.json and, for each Jira key, fetches the issue with its
changelog from the public Apache Jira REST API. No login, no API key, no
download: Apache's tracker is open to anonymous read access.

Why this and not the 5.8 GB Zenodo dump: the dump is a MongoDB export that
needs MongoDB installed and restored before a single query. The live API gives
the same fields for exactly the issues we need, in minutes, and is
reproducible by anyone reading the thesis. The Zenodo dataset is still cited:
it is what identifies Apache as a suitable repository and documents the
field semantics (Montgomery, Lueders & Maalej, MSR 2022).

Stdlib only -- nothing to pip install.
Safe to stop and re-run: completed issues are skipped.

Output: jira_issues.json
"""
import json, os, re, sys, time, urllib.request, urllib.error

BASE = "https://issues.apache.org/jira/rest/api/2/issue"
FIELDS = "summary,description,created,resolutiondate,status,resolution,fixVersions,issuetype,priority,labels,reporter"
OUT = "jira_issues.json"
PAUSE = 0.35          # be a polite citizen of someone else's server
RETRIES = 3
TIMEOUT = 30


def fetch(key):
    url = f"{BASE}/{key}?fields={FIELDS}&expand=changelog"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json",
        # Identify the client honestly; some Apache endpoints reject blank agents.
        "User-Agent": "BTH-thesis-research/1.0 (academic; traceability study)",
    })
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (404, 403):
                return {"_error": f"HTTP {e.code}"}
            if e.code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            if attempt == RETRIES - 1:
                return {"_error": f"HTTP {e.code}"}
        except Exception as e:
            if attempt == RETRIES - 1:
                return {"_error": type(e).__name__}
        time.sleep(2 * (attempt + 1))
    return {"_error": "retries exhausted"}


def text_changes(issue):
    """Every recorded edit to the summary or description field, oldest first."""
    out = []
    for h in issue.get("changelog", {}).get("histories", []):
        for it in h.get("items", []):
            if it.get("field") in ("description", "summary"):
                frm, to = it.get("fromString") or "", it.get("toString") or ""
                if frm.strip() and to.strip() and frm.strip() != to.strip():
                    out.append({
                        "field": it["field"],
                        "when": h.get("created"),
                        "old_text": frm,
                        "new_text": to,
                    })
    out.sort(key=lambda d: d["when"] or "")
    return out


def main():
    if not os.path.exists("mined_links.json"):
        sys.exit("mined_links.json not found -- run it in the same folder as this script.")

    d = json.load(open("mined_links.json", encoding="utf-8"))
    keys = [r["key"] for r in d["sample_linked"]] + [r["key"] for r in d["sample_unlinked"]]

    done = {}
    if os.path.exists(OUT):
        try:
            done = json.load(open(OUT, encoding="utf-8"))
            print(f"resuming -- {len(done)} already fetched")
        except Exception:
            done = {}

    todo = [k for k in keys if k not in done]
    print(f"{len(keys)} issues total, {len(todo)} to fetch")
    print(f"estimated time: {len(todo)*PAUSE/60:.1f} min\n")

    t0, errs, changed = time.time(), 0, 0
    for i, k in enumerate(todo, 1):
        iss = fetch(k)
        if "_error" in iss:
            done[k] = {"key": k, "error": iss["_error"]}
            errs += 1
        else:
            f = iss.get("fields", {}) or {}
            ch = text_changes(iss)
            if ch:
                changed += 1
            done[k] = {
                "key": k,
                "summary": f.get("summary") or "",
                "description": f.get("description") or "",
                "created": f.get("created"),
                "resolved": f.get("resolutiondate"),
                "status": ((f.get("status") or {}).get("name")),
                "resolution": ((f.get("resolution") or {}).get("name")),
                "issuetype": ((f.get("issuetype") or {}).get("name")),
                "priority": ((f.get("priority") or {}).get("name")),
                "labels": f.get("labels") or [],
                "fix_versions": [v.get("name") for v in (f.get("fixVersions") or [])],
                # reporter kept only as an opaque id -- see anonymisation note in the report
                "reporter_key": ((f.get("reporter") or {}).get("key")),
                "text_changes": ch,
            }

        if i % 25 == 0 or i == len(todo):
            el = time.time() - t0
            rate = i / el if el else 0
            left = (len(todo) - i) / rate if rate else 0
            print(f"  {i}/{len(todo)}  errors={errs}  with-text-changes={changed}  "
                  f"eta {left/60:.1f} min")
            with open(OUT, "w", encoding="utf-8") as fh:
                json.dump(done, fh, indent=1)

        time.sleep(PAUSE)

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(done, fh, indent=1)

    good = [v for v in done.values() if "error" not in v]
    wch = [v for v in good if v.get("text_changes")]
    print(f"\n{'='*58}")
    print(f"  fetched OK                  {len(good):>6}")
    print(f"  errors                      {len(done)-len(good):>6}")
    print(f"  with requirement edits (RQ3){len(wch):>6}   <- these drive RQ3")
    print(f"  total recorded edits        {sum(len(v['text_changes']) for v in wch):>6}")
    print(f"{'='*58}")
    print(f"\nwrote {OUT}  -- next: python build_csvs.py")


if __name__ == "__main__":
    main()
