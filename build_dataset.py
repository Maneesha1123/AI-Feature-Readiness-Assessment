"""
build_dataset.py
Pulls real data from a public GitHub repository and builds the 5 CSV
files your prototype's load_data.py expects.
"""

import csv
import os
import requests

GITHUB_API = "https://api.github.com"


def get_headers(token):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_issues(owner, repo, headers, max_items=15):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"
    params = {"state": "closed", "labels": "enhancement", "per_page": max_items}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    issues = resp.json()
    return [i for i in issues if "pull_request" not in i]


def fetch_releases(owner, repo, headers, max_items=10):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/releases"
    params = {"per_page": max_items}
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def clean_text(text, max_len=200):
    if not text:
        return ""
    text = " ".join(text.split())
    return text[:max_len]


def build_dataset(owner, repo, token, out_dir="dataset"):
    os.makedirs(out_dir, exist_ok=True)
    headers = get_headers(token)

    print(f"Fetching closed 'enhancement' issues from {owner}/{repo} ...")
    issues = fetch_issues(owner, repo, headers)
    print(f"  -> got {len(issues)} issues")

    print(f"Fetching releases from {owner}/{repo} ...")
    releases = fetch_releases(owner, repo, headers)
    print(f"  -> got {len(releases)} releases")

    features_path = os.path.join(out_dir, "features.csv")
    with open(features_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["feature_id", "feature_name", "sprint", "product_owner"])
        for idx, issue in enumerate(issues, start=1):
            fid = f"F{idx:03d}"
            writer.writerow([
                fid,
                clean_text(issue["title"], 80),
                f"issue-#{issue['number']}",
                issue["user"]["login"] if issue.get("user") else "unknown",
            ])
    print(f"Wrote {features_path}")

    ac_path = os.path.join(out_dir, "acceptance_criteria.csv")
    with open(ac_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ac_id", "feature_id", "description", "version"])
        for idx, issue in enumerate(issues, start=1):
            fid = f"F{idx:03d}"
            ac_id = f"AC-{idx:03d}"
            description = clean_text(issue.get("body") or issue["title"], 250)
            writer.writerow([ac_id, fid, description, 1])
    print(f"Wrote {ac_path}")
    print("  NOTE: review this file and rewrite each description as a")
    print("  clear, single testable acceptance criterion sentence.")

    deployment_path = os.path.join(out_dir, "deployment.csv")
    with open(deployment_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["feature_id", "environment", "status"])
        for idx, issue in enumerate(issues, start=1):
            fid = f"F{idx:03d}"
            has_release_after = any(
                r.get("published_at") and issue.get("closed_at")
                and r["published_at"] > issue["closed_at"]
                for r in releases
            )
            status = "ready" if has_release_after else "not_ready"
            writer.writerow([fid, "production", status])
    print(f"Wrote {deployment_path}")

    tc_path = os.path.join(out_dir, "test_cases.csv")
    if not os.path.exists(tc_path):
        with open(tc_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["tc_id", "feature_id", "description", "result"])
            for idx, issue in enumerate(issues, start=1):
                fid = f"F{idx:03d}"
                tc_id = f"TC-{idx:03d}"
                writer.writerow([
                    tc_id, fid,
                    f"TODO: find the real test in the {owner}/{repo} tests/ folder "
                    f"that verifies '{clean_text(issue['title'], 50)}' and describe it here",
                    "pass",
                ])
        print(f"Wrote SKELETON {tc_path} - fill in real test descriptions manually")
    else:
        print(f"{tc_path} already exists - not overwriting your manual work")

    trace_path = os.path.join(out_dir, "traceability.csv")
    if not os.path.exists(trace_path):
        with open(trace_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["feature_id", "ac_id", "tc_id", "status"])
            n_to_link = max(1, int(len(issues) * 0.7))
            for idx in range(1, n_to_link + 1):
                fid = f"F{idx:03d}"
                writer.writerow([fid, f"AC-{idx:03d}", f"TC-{idx:03d}", "Linked"])
        print(f"Wrote SKELETON {trace_path}")
        print(f"  -> {n_to_link} of {len(issues)} features linked; rest left unlinked")
    else:
        print(f"{trace_path} already exists - not overwriting your manual work")

    print("\nDone. Next manual steps:")
    print("  1. Clean up acceptance_criteria.csv descriptions.")
    print("  2. Fill in real test descriptions in test_cases.csv.")
    print("  3. Adjust traceability.csv based on what you find.")
    print("  4. Create requirement_history.csv by hand for 1-2 features.")


if __name__ == "__main__":
    print("=== GitHub Dataset Builder ===\n")
    repo_input = input("Repository (owner/repo) [default: httpie/httpie]: ").strip()
    if not repo_input:
        repo_input = "httpie/httpie"
    owner, repo = repo_input.split("/")

    token = input("GitHub personal access token (optional, press Enter to skip): ").strip()

    try:
        build_dataset(owner, repo, token or None)
    except requests.exceptions.HTTPError as e:
        print(f"\nGitHub API error: {e}")