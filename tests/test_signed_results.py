"""
Tests for Signed Results (Slice 10.3).
Verifies that Findings payloads can be signed and verified via the API logic.
"""

import pytest

from cns_py.api.server import ResultVerifyRequest, verify_result_endpoint
from cns_py.crypto import signing


@pytest.fixture
def keypair():
    priv = signing.generate_private_key()
    pub = priv.public_key()
    # Serialize pub to hex
    pub_bytes = pub.public_bytes(
        encoding=signing.serialization.Encoding.Raw, format=signing.serialization.PublicFormat.Raw
    )
    return priv, pub_bytes.hex()


def test_sign_and_verify_result(keypair):
    priv, pub_hex = keypair

    # 1. Create a Findings payload
    findings = {"plan_id": "plan_123", "results": [{"step_index": 0, "status": "ok"}]}

    # 2. Sign it
    sig = signing.sign_claim(findings, priv)

    # 3. Verify via Endpoint Logic
    req = ResultVerifyRequest(result_payload=findings, signature=sig, public_key=pub_hex)

    resp = verify_result_endpoint(req)
    assert resp.valid is True
    assert resp.result_hash is not None


def test_tampered_result_fails(keypair):
    priv, pub_hex = keypair
    findings = {"test": "ok"}
    sig = signing.sign_claim(findings, priv)

    # Tamper with payload
    tampered_findings = {"test": "ko"}

    req = ResultVerifyRequest(
        result_payload=tampered_findings,
        signature=sig,  # Signature matches original, not tampered
        public_key=pub_hex,
    )

    resp = verify_result_endpoint(req)
    assert resp.valid is False
    assert resp.reason == "Signature Mismatch"


def test_invalid_key_fails(keypair):
    priv, _ = keypair
    findings = {"test": "ok"}
    sig = signing.sign_claim(findings, priv)

    req = ResultVerifyRequest(
        result_payload=findings,
        signature=sig,
        public_key="deadbeef",  # Invalid hex length for Ed25519 (needs 32 bytes = 64 hex)
    )

    resp = verify_result_endpoint(req)
    assert resp.valid is False
    assert "Invalid Key" in resp.reason
