"""
End-to-End Demo of Signed Provenance with Executable Memory (WASM).
Simulates a 'Compliance Check':
1. Alice creates a Claim (Input).
2. Alice signs the Claim.
3. System (Executor) loads a Rule (WASM).
4. Executor runs Rule(Input) -> Result.
5. Executor signs Result (linking to Input and Rule).
6. Auditor verifies the entire chain.
"""

import hashlib

from cns_py.crypto import canonicalize, generate_private_key, sign_claim, verify_claim
from cns_py.wasm import execute_rule

# Minimal No-Op Rule (simulates "Always Compliant")
# In a real scenario, this would check input logic.
RULE_WASM_WAT = """
(module
    (memory (export "memory") 1)
    (func (export "_start")
        (nop)
    )
)
"""


def test_provenance_compliance_demo():
    # --- Actors Setup ---
    alice_key = generate_private_key()
    alice_pub = alice_key.public_key()

    executor_key = generate_private_key()
    executor_pub = executor_key.public_key()

    # --- Step 1: Alice creates Claim ---
    input_claim = {"resource": "s3::my-bucket", "configuration": "TLS_1_2", "timestamp": 1234567890}

    # --- Step 2: Alice signs Claim ---
    input_signature = sign_claim(input_claim, alice_key)

    # Bundle Input
    signed_input = {
        "payload": input_claim,
        "signature": input_signature,
        "signer": "alice",  # In real app, PubKey Ref
    }

    # --- Step 3: Executor loads Rule ---
    # Convert WAT to Bytes (simulating loading binary)
    rule_bytes = RULE_WASM_WAT.encode("utf-8")
    rule_hash = hashlib.sha256(rule_bytes).hexdigest()

    # --- Step 4: Execute Rule ---
    # Executor validates input first
    assert verify_claim(signed_input["payload"], signed_input["signature"], alice_pub)

    # Run Sandbox
    # For this demo, NOOP returns {} (empty dict)
    # Ideally our rule would return {"status": "compliant"}
    # Since we use NOOP, we assume empty means "Run Successful" and we augment result.
    raw_result = execute_rule(rule_bytes, signed_input["payload"])

    # Simulator logic: If execution succeeded (didn't trap), we deem it compliant for this demo
    compliance_result = {
        "status": "compliant",
        "rule_id": rule_hash,
        "input_hash": hashlib.sha256(canonicalize(input_claim)).hexdigest(),
        "raw_output": raw_result,
    }

    # --- Step 5: Executor signs Result ---
    result_signature = sign_claim(compliance_result, executor_key)

    signed_result = {
        "payload": compliance_result,
        "signature": result_signature,
        "executor": "node-1",
    }

    # --- Step 6: Auditor Verification ---
    # Auditor has Signed Result and Signed Input

    # A. Verify Result Signature
    assert verify_claim(signed_result["payload"], signed_result["signature"], executor_pub)

    # B. Verify Result links to Input
    input_canon = canonicalize(signed_input["payload"])
    computed_input_hash = hashlib.sha256(input_canon).hexdigest()
    assert signed_result["payload"]["input_hash"] == computed_input_hash

    # C. Verify Input Signature
    assert verify_claim(signed_input["payload"], signed_input["signature"], alice_pub)

    print("\n[Demo] Compliance Chain Verified Successfully!")
