---
name: jwt_attacks
description: JWT attack methodology - algorithm confusion, signature stripping, claim tampering
category: vulnerabilities
version: "1.0"
last_updated: "2026-03-26"
requires: [caido_operations]
applies_to: [api, exploit]
---

# JWT Attack Methodology

## Reconnaissance

1. Intercept traffic and identify JWT tokens (Base64 with two dots: `xxxxx.yyyyy.zzzzz`)
2. Decode header to determine algorithm: `alg` field
3. Decode payload to identify claims: `sub`, `role`, `exp`, `iss`

Use `caido_httpql_search(query="resp.header.name:authorization")` to find JWT usage.

## Attack Sequence - Try in Order

### Attack 1: Algorithm None

Change the header `alg` to `none` and remove the signature:
```
exploit_jwt(token="<captured_jwt>", attack="alg_none")
```

If the server accepts it, any claim can be forged. **Critical vulnerability.**

### Attack 2: Signature Stripping

Remove the signature entirely (everything after the second dot):
```
exploit_jwt(token="<captured_jwt>", attack="strip_signature")
```

Some implementations only validate signature when present.

### Attack 3: Algorithm Confusion (RS256 -> HS256)

If the server uses RS256 (asymmetric), try signing with HS256 using the **public key** as the HMAC secret:
```
exploit_jwt(token="<captured_jwt>", attack="hmac_confusion", public_key="<server_public_key>")
```

This works when the server uses the same key variable for both RSA verification and HMAC verification.

### Attack 4: Claim Tampering

Modify claims in the payload to escalate privileges:
```
exploit_jwt(
    token="<captured_jwt>",
    attack="claim_tamper",
    claims='{"role": "admin", "sub": "victim_user_id"}'
)
```

Test with each attack method to find one that validates.

### Attack 5: Expired Token Reuse

Try using an expired token - some servers don't check `exp`:
```
exploit_jwt(token="<expired_jwt>", attack="claim_tamper", claims='{}')
```

### Attack 6: Key ID (kid) Injection

If the JWT header has a `kid` field, try:
- SQL injection: `kid: "' UNION SELECT 'secret' --"`
- Path traversal: `kid: "../../dev/null"`
- Known key: `kid: "public_key_id"`

## Decision Tree

```
JWT found in traffic?
|-- Decode header -> check alg
|   |-- RS256 -> Try alg:none, then HS256 confusion
|   |-- HS256 -> Try alg:none, then brute-force weak keys
|   +-- none already -> Already vulnerable!
|-- Check exp claim
|   +-- Expired? -> Try replaying anyway
+-- Check role/admin claims
    +-- Present? -> Try claim tampering with each attack
```

## Reporting

| Attack | Severity |
|--------|----------|
| alg:none accepted | CRITICAL |
| RS256->HS256 confusion | CRITICAL |
| Signature not validated | CRITICAL |
| Expired tokens accepted | HIGH |
| Claim tampering (with valid sig) | Depends on impact |
