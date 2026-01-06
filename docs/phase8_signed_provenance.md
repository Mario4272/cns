# Phase 8: Signed Provenance (RFC)

## Overview
To trust the output of an Executable Memory system (Smart Graph), every claim must be attributable to a signer. We use **Ed25519** signatures over a **canonicalized** representation of the claim.

## 1. Canonicalization
Signatures are brittle if the underlying byte representation changes (e.g., JSON key ordering). We enforce a strict canonical form.

### Rules (RFC 8785 subset)
1. **Ordering**: Object keys must be sorted lexicographically by UTF-16 code unit (standard JSON sorting).
2. **Whitespace**: No whitespace allowed.
3. **Floats**: Must be stripped of trailing zeros? *Decision*: For v1, we enforce `str` for values or strict integer types. Floats in claims are risky. If needed, standard IEEE 754 representation or string serialization.
4. **Encoding**: UTF-8.

Pseudocode:
```python
import json
def canonicalize(data: Any) -> bytes:
    # sort_keys=True ensures key order
    # separators=(',', ':') removes whitespace
    return json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
```

## 2. Signing
- **Algorithm**: Ed25519 (Edwards-curve Digital Signature Algorithm).
- **Library**: `cryptography` (Python).
- **Key Format**: Raw 32-byte private seed, 32-byte public key.
- **Output**: Hex-encoded string of the signature (64 bytes -> 128 hex chars).

## 3. Data Model
A signed claim wraps the payload:

```json
{
  "payload": {
    "subject": "uuid-...",
    "predicate": "tells",
    "object": "content-...",
    "as_of": "2025-01-01T00:00:00Z"
  },
  "provenance": {
    "signer_id": "source-123",
    "signature": "hex-signature...",
    "alg": "ed25519"
  }
}
```

The signature is computed over `canonicalize(payload)`.

## 4. Verification API
`POST /provenance/verify`

**Request**:
```json
{
  "payload": { ... },
  "signature": "...",
  "public_key": "hex-key..." 
}
```

**Response**:
```json
{
  "valid": true,
  "claim_hash": "sha256-hash-of-canonical-payload"
}
```
