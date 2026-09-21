import requests


GITHUB_API = "https://api.github.com"


def get_repository_issues(
    owner: str,
    repo: str,
    state: str = "all",
    max_pages: int = 5
):
    issues = []

    headers = {
        "Accept": "application/vnd.github+json"
    }

    for page in range(1, max_pages + 1):

        url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"

        params = {
            "state": state,
            "per_page": 100,
            "page": page
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        page_data = response.json()

        if not page_data:
            break

        # GitHub's Issues API also returns pull requests.
        # We only want actual issues.
        for issue in page_data:
            if "pull_request" not in issue:
                issues.append(issue)

        if len(page_data) < 100:
            break

    return issues


def get_issue(
    owner: str,
    repo: str,
    issue_number: int
):
    """Get one GitHub issue."""

    url = (
        f"{GITHUB_API}/repos/{owner}/{repo}"
        f"/issues/{issue_number}"
    )

    headers = {
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def get_issue_timeline(
    owner: str,
    repo: str,
    issue_number: int
):
    """Get the timeline/events associated with an issue."""

    url = (
        f"{GITHUB_API}/repos/{owner}/{repo}"
        f"/issues/{issue_number}/timeline"
    )

    headers = {
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(
        url,
        headers=headers,
        params={"per_page": 100},
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def get_pull_request(
    owner: str,
    repo: str,
    pull_number: int
):
    """Get one pull request."""

    url = (
        f"{GITHUB_API}/repos/{owner}/{repo}"
        f"/pulls/{pull_number}"
    )

    headers = {
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def get_pull_request_files(
    owner: str,
    repo: str,
    pull_number: int
):
    """Get files changed by a pull request."""

    url = (
        f"{GITHUB_API}/repos/{owner}/{repo}"
        f"/pulls/{pull_number}/files"
    )

    headers = {
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(
        url,
        headers=headers,
        params={"per_page": 100},
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def get_repository_file(
    owner: str,
    repo: str,
    path: str,
    ref: str = "main"
):
    """Get the contents of a repository file."""

    url = (
        f"{GITHUB_API}/repos/{owner}/{repo}"
        f"/contents/{path}"
    )

    headers = {
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(
        url,
        headers=headers,
        params={"ref": ref},
        timeout=30
    )

    response.raise_for_status()

    return response.json()