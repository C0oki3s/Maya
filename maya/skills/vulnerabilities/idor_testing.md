---
name: idor_testing
description: Methodology for testing Insecure Direct Object Reference vulnerabilities in mobile APIs
category: vulnerabilities
version: "1.0"
last_updated: "2026-03-26"
requires: [caido_operations]
applies_to: [api, exploit]
---

# IDOR Testing Methodology

## What is IDOR

Insecure Direct Object Reference - when an API uses a user-controllable identifier (ID, UUID, filename) to access objects without verifying the caller owns that object.

## Step-by-Step Testing Process

### 1. Identify Candidate Endpoints

Look for API calls that reference objects by ID:
```
GET /api/users/{user_id}/profile
GET /api/orders/{order_id}
GET /api/documents/{doc_id}/download
PUT /api/accounts/{account_id}/settings
DELETE /api/messages/{message_id}
```

Use `caido_httpql_search` to find these patterns:
```
caido_httpql_search(query="path.regex:/[0-9]+/ AND resp.code:200")
```

### 2. Create Two Test Accounts

You need two authenticated sessions:
- Account A: the "attacker"
- Account B: the "victim"

Capture auth tokens for both.

### 3. Test Each Endpoint

For each candidate endpoint:

1. Make the request as Account B - note the resource ID
2. Make the same request as Account A using Account B's resource ID
3. Compare responses

Use `exploit_idor`:
```
exploit_idor(
    endpoint="/api/users/VICTIM_ID/profile",
    method="GET",
    original_id="VICTIM_ID",
    test_ids="ATTACKER_ID,0,1,999999",
    auth_header="Bearer ATTACKER_TOKEN"
)
```

### 4. Interpret Results

| Result | Meaning |
|--------|---------|
| 200 with victim data | **CONFIRMED IDOR** - Critical finding |
| 200 with attacker data | No IDOR - server resolved to caller's own data |
| 403/401 | Proper authorization - no IDOR |
| 404 | May be IDOR-safe OR ID format wrong - try sequential IDs |
| 500 | Server error - may indicate SQL injection instead |

### 5. ID Enumeration Strategies

- **Sequential integers**: Try current_id +/- 1, +/- 10, 0, 1
- **UUIDs**: If predictable (v1), extract timestamp and generate adjacent UUIDs
- **Encoded IDs**: Base64-decode, modify, re-encode
- **Hashed IDs**: If using MD5/SHA1 of sequential values, generate the hash

### 6. Beyond Read - Test Write/Delete

IDOR on read is informational. IDOR on write/delete is critical:
```
PUT /api/users/VICTIM_ID/profile  (modify someone's profile)
DELETE /api/orders/VICTIM_ID       (cancel someone's order)
POST /api/transfers               (transfer from someone's account)
```

## Reporting

When reporting IDOR:
- Severity: HIGH (read) or CRITICAL (write/delete)
- Include: endpoint, HTTP method, request/response diff
- Impact: what data was accessed or modified
