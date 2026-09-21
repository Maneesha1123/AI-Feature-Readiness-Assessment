import pandas as pd
import os

os.makedirs("dataset", exist_ok=True)

# ============================================================
# FEATURES
# ============================================================

features = pd.DataFrame([
    ["F001", "User Login", "Sprint 1", "Alice"],
    ["F002", "User Registration", "Sprint 1", "Alice"],
    ["F003", "Shopping Cart", "Sprint 2", "Bob"],
    ["F004", "Checkout", "Sprint 2", "Bob"],
    ["F005", "Order Tracking", "Sprint 3", "Charlie"],

    # Real GitHub-derived feature
    ["GH-2014", "IP-aware response deduplication", "GitHub", "ProjectDiscovery"]

], columns=[
    "feature_id",
    "feature_name",
    "sprint",
    "product_owner"
])


# ============================================================
# ACCEPTANCE CRITERIA
# ============================================================

acceptance = pd.DataFrame([
    ["AC001", "F001", "Login with valid credentials", 1],
    ["AC002", "F002", "Register new user", 1],
    ["AC003", "F003", "Add products to cart", 1],
    ["AC004", "F004", "Complete checkout", 1],
    ["AC005", "F005", "Track order", 1],

    # GitHub-derived acceptance criteria
    ["AC-GH2014-01", "GH-2014",
     "Responses with the same or sufficiently similar content and the same IP are treated as duplicates.", 1],

    ["AC-GH2014-02", "GH-2014",
     "Responses with the same or sufficiently similar content but different IPs are not treated as duplicates.", 1],

    ["AC-GH2014-03", "GH-2014",
     "Responses with different content are not treated as duplicates even when the IP is the same.", 1],

    ["AC-GH2014-04", "GH-2014",
     "Near-duplicate response content is treated as duplicate when the SimHash distance is less than or equal to 3 and the IP is the same.", 1],

    ["AC-GH2014-05", "GH-2014",
     "Near-duplicate response content with different IPs is not treated as duplicate.", 1],

    ["AC-GH2014-06", "GH-2014",
     "When the response IP is empty deduplication falls back to content similarity.", 1],

    ["AC-GH2014-07", "GH-2014",
     "Multiple subdomains returning the same or similar content from the same IP are deduplicated.", 1],

    ["AC-GH2014-08", "GH-2014",
     "Multiple subdomains returning the same or similar content from different IPs are retained separately.", 1]

], columns=[
    "ac_id",
    "feature_id",
    "description",
    "version"
])


# ============================================================
# TEST CASES
# ============================================================

tests = pd.DataFrame([
    ["TC001", "F001", "Verify valid login", "Pass"],
    ["TC002", "F002", "Verify registration", "Pass"],
    ["TC003", "F003", "Verify cart", "Pass"],
    ["TC004", "F004", "Verify checkout", "Fail"],
    ["TC005", "F005", "Verify tracking", "Pass"],

    # GitHub-derived test cases
    ["TC-GH2014-01", "GH-2014",
     "same content same IP is duplicate", "Pass"],

    ["TC-GH2014-02", "GH-2014",
     "same content different IP is NOT duplicate", "Pass"],

    ["TC-GH2014-03", "GH-2014",
     "different content same IP is NOT duplicate", "Pass"],

    ["TC-GH2014-04", "GH-2014",
     "different content different IP is NOT duplicate", "Pass"],

    ["TC-GH2014-05", "GH-2014",
     "third subdomain same content same IP is duplicate", "Pass"],

    ["TC-GH2014-06", "GH-2014",
     "near-duplicate content same IP is duplicate", "Pass"],

    ["TC-GH2014-07", "GH-2014",
     "near-duplicate content different IP is NOT duplicate", "Pass"],

    ["TC-GH2014-08", "GH-2014",
     "empty IP falls back to content-only dedup", "Pass"],

    ["TC-GH2014-09", "GH-2014",
     "many subdomains same default page same IP", "Pass"],

    ["TC-GH2014-10", "GH-2014",
     "many subdomains same default page different IPs", "Pass"]

], columns=[
    "tc_id",
    "feature_id",
    "description",
    "result"
])


# ============================================================
# TRACEABILITY
# ============================================================

traceability = pd.DataFrame([
    ["F001", "AC001", "TC001", "Linked"],
    ["F002", "AC002", "TC002", "Linked"],
    ["F003", "AC003", "TC003", "Linked"],
    ["F004", "AC004", "TC004", "Broken"],
    ["F005", "AC005", "TC005", "Linked"],

    # GitHub-derived ground truth
    ["GH-2014", "AC-GH2014-01", "TC-GH2014-01", "Linked"],
    ["GH-2014", "AC-GH2014-01", "TC-GH2014-05", "Linked"],
    ["GH-2014", "AC-GH2014-02", "TC-GH2014-02", "Linked"],
    ["GH-2014", "AC-GH2014-03", "TC-GH2014-03", "Linked"],
    ["GH-2014", "AC-GH2014-04", "TC-GH2014-06", "Linked"],
    ["GH-2014", "AC-GH2014-05", "TC-GH2014-07", "Linked"],
    ["GH-2014", "AC-GH2014-06", "TC-GH2014-08", "Linked"],
    ["GH-2014", "AC-GH2014-07", "TC-GH2014-09", "Linked"],
    ["GH-2014", "AC-GH2014-08", "TC-GH2014-10", "Linked"]

], columns=[
    "feature_id",
    "ac_id",
    "tc_id",
    "status"
])


# ============================================================
# DEPLOYMENT
# ============================================================

deployment = pd.DataFrame([
    ["F001", "QA", "Ready"],
    ["F002", "QA", "Ready"],
    ["F003", "QA", "Ready"],
    ["F004", "QA", "Pending"],
    ["F005", "QA", "Ready"]
], columns=[
    "feature_id",
    "environment",
    "status"
])


# ============================================================
# SAVE CSV FILES
# ============================================================

features.to_csv("dataset/features.csv", index=False)
acceptance.to_csv("dataset/acceptance_criteria.csv", index=False)
tests.to_csv("dataset/test_cases.csv", index=False)
traceability.to_csv("dataset/traceability.csv", index=False)
deployment.to_csv("dataset/deployment.csv", index=False)

print("Dataset created successfully!")
print(f"Features: {len(features)}")
print(f"Acceptance Criteria: {len(acceptance)}")
print(f"Test Cases: {len(tests)}")
print(f"Traceability Links: {len(traceability)}")
print(f"Deployment Records: {len(deployment)}")

