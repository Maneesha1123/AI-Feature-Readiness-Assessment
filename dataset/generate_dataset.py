import pandas as pd
import os

os.makedirs("dataset", exist_ok=True)

features = pd.DataFrame([
    ["F001", "User Login", "Sprint 1", "Alice"],
    ["F002", "User Registration", "Sprint 1", "Alice"],
    ["F003", "Shopping Cart", "Sprint 2", "Bob"],
    ["F004", "Checkout", "Sprint 2", "Bob"],
    ["F005", "Order Tracking", "Sprint 3", "Charlie"]
], columns=[
    "feature_id",
    "feature_name",
    "sprint",
    "product_owner"
])

acceptance = pd.DataFrame([
    ["AC001","F001","Login with valid credentials",1],
    ["AC002","F002","Register new user",1],
    ["AC003","F003","Add products to cart",1],
    ["AC004","F004","Complete checkout",1],
    ["AC005","F005","Track order",1]
], columns=[
    "ac_id",
    "feature_id",
    "description",
    "version"
])

tests = pd.DataFrame([
    ["TC001","F001","Verify valid login","Pass"],
    ["TC002","F002","Verify registration","Pass"],
    ["TC003","F003","Verify cart","Pass"],
    ["TC004","F004","Verify checkout","Fail"],
    ["TC005","F005","Verify tracking","Pass"]
], columns=[
    "tc_id",
    "feature_id",
    "description",
    "result"
])

traceability = pd.DataFrame([
    ["F001","AC001","TC001","Linked"],
    ["F002","AC002","TC002","Linked"],
    ["F003","AC003","TC003","Linked"],
    ["F004","AC004","TC004","Broken"],
    ["F005","AC005","TC005","Linked"]
], columns=[
    "feature_id",
    "ac_id",
    "tc_id",
    "status"
])

deployment = pd.DataFrame([
    ["F001","QA","Ready"],
    ["F002","QA","Ready"],
    ["F003","QA","Ready"],
    ["F004","QA","Pending"],
    ["F005","QA","Ready"]
], columns=[
    "feature_id",
    "environment",
    "status"
])

features.to_csv("dataset/features.csv", index=False)
acceptance.to_csv("dataset/acceptance_criteria.csv", index=False)
tests.to_csv("dataset/test_cases.csv", index=False)
traceability.to_csv("dataset/traceability.csv", index=False)
deployment.to_csv("dataset/deployment.csv", index=False)

print("Dataset created successfully!")