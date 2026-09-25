import os

os.makedirs("dataset", exist_ok=True)

files = {
"acceptance_criteria.csv": """ac_id,feature_id,description,version
AC-003,F003,Users can use a short verify=no shortcut flag instead of typing the full option name to disable SSL verification.,1
AC-004,F004,When no hostname is passed HTTPie must default the request to localhost so that commands like http :8080 work correctly.,2
AC-007,F007,Sessions must support multiple headers that share the same name instead of overwriting earlier values with later ones.,1
AC-009,F009,HTTPie must detect DNS resolution failures and display a clear useful error message instead of a generic connection error.,1
AC-012,F012,HTTPie must support Bearer token authentication by allowing users to pass a token that is sent in the Authorization header.,1
AC-014,F014,HTTPie must accept a shorthand where a colon-slash-slash prefix is interpreted as using the following word as the URL scheme.,1
AC-GH2014-01,GH-2014,Responses with the same or sufficiently similar content and the same IP are treated as duplicates.,1
AC-GH2014-02,GH-2014,Responses with the same or sufficiently similar content but different IPs are not treated as duplicates.,1
AC-GH2014-03,GH-2014,Responses with different content are not treated as duplicates even when the IP is the same.,1
AC-GH2014-04,GH-2014,Near-duplicate response content is treated as duplicate when the SimHash distance is less than or equal to 3 and the IP is the same.,2
AC-GH2014-05,GH-2014,Near-duplicate response content with different IPs is not treated as duplicate.,1
AC-GH2014-06,GH-2014,When the response IP is empty deduplication falls back to content similarity.,1
AC-GH2014-07,GH-2014,Multiple subdomains returning the same or similar content from the same IP are deduplicated.,1
AC-GH2014-08,GH-2014,Multiple subdomains returning the same or similar content from different IPs are retained separately.,1
""",

"features.csv": """feature_id,feature_name,sprint,product_owner
F003,Add shortcut to --verify=no,issue-#1536,franciscobretal
F004,Default to localhost,issue-#1519,sayanarijit
F007,Sessions doesn't support multiple headers sharing the same name,issue-#1331,ducaale
F009,Gracefully handle DNS failures,issue-#1248,isidentical
F012,Support Bearer Authentication,issue-#1215,isidentical
F014,:// to use command name for scheme,issue-#1195,sevenc-nanashi
GH-2014,Duplicate response detection across subdomains,issue-#2014,Pooja-prad
""",

"test_cases.csv": """tc_id,feature_id,description,result
TC-003,F003,Verify that the shortcut flag correctly disables SSL certificate verification,pass
TC-004,F004,Verify that HTTPie does not error out and attempts a reasonable default connection when no hostname is passed,pass
TC-007,F007,Verify that a session correctly stores two headers with the same name without overwriting,pass
TC-009,F009,Verify that an invalid hostname produces a clear DNS failure message,pass
TC-012,F012,Verify that requests include an Authorization header with a Bearer token when authentication is configured,pass
TC-014,F014,Verify that a request with no hostname defaults to localhost,pass
TC-GH2014-01,GH-2014,same content same IP is duplicate,pass
TC-GH2014-02,GH-2014,same content different IP is NOT duplicate,pass
TC-GH2014-03,GH-2014,different content same IP is NOT duplicate,pass
TC-GH2014-04,GH-2014,different content different IP is NOT duplicate,pass
TC-GH2014-05,GH-2014,third subdomain same content same IP is duplicate,pass
TC-GH2014-06,GH-2014,near-duplicate content is duplicate when hashes are close and the IP matches,pass
TC-GH2014-07,GH-2014,near-duplicate content different IP is NOT duplicate,pass
TC-GH2014-08,GH-2014,empty IP falls back to content-only dedup,pass
TC-GH2014-09,GH-2014,many subdomains same default page same IP,pass
TC-GH2014-10,GH-2014,many subdomains same default page different IPs,pass
""",

"traceability.csv": """feature_id,ac_id,tc_id,status
F003,AC-003,TC-003,Linked
F004,AC-004,TC-004,Linked
F007,AC-007,TC-007,Linked
F009,AC-009,TC-009,Linked
F014,AC-014,TC-014,Linked
GH-2014,AC-GH2014-01,TC-GH2014-01,Linked
GH-2014,AC-GH2014-02,TC-GH2014-02,Linked
GH-2014,AC-GH2014-03,TC-GH2014-03,Linked
GH-2014,AC-GH2014-04,TC-GH2014-06,Linked
GH-2014,AC-GH2014-05,TC-GH2014-07,Linked
GH-2014,AC-GH2014-07,TC-GH2014-09,Linked
GH-2014,AC-GH2014-08,TC-GH2014-10,Linked
""",

"deployment.csv": """feature_id,environment,status
F003,production,ready
F004,production,not_ready
F007,production,ready
F009,production,ready
F012,production,not_ready
F014,production,ready
GH-2014,production,not_ready
""",

"requirement_history.csv": """feature_id,ac_id,old_text,new_text
F004,AC-004,When no hostname is passed HTTPie should not error out and should attempt a reasonable default connection.,When no hostname is passed HTTPie must default the request to localhost so that commands like http :8080 work correctly.
GH-2014,AC-GH2014-04,Near-duplicate response content is treated as duplicate when the content is broadly similar and the IP is the same.,Near-duplicate response content is treated as duplicate when the SimHash distance is less than or equal to 3 and the IP is the same.
""",
}

for name, content in files.items():
    path = os.path.join("dataset", name)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    print("wrote", path)

print("\nAll six files written.")