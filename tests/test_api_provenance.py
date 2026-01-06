"""
Integration tests for /provenance/verify endpoint.
"""
from fastapi.testclient import TestClient
from cns_py.api.server import app
from cns_py.crypto import generate_private_key, sign_claim, canonicalize
from cryptography.hazmat.primitives import serialization
import hashlib

client = TestClient(app)

def test_provenance_verify_happy_path():
    """Verify endpoint accepts valid signature."""
    # 1. Setup Keys
    priv = generate_private_key()
    pub = priv.public_key()
    
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    pub_hex = pub_bytes.hex()
    
    # 2. Sign Claim
    payload = {"sub": "alice", "action": "write"}
    sig = sign_claim(payload, priv)
    
    # 3. Call API
    resp = client.post("/provenance/verify", json={
        "payload": payload,
        "signature": sig,
        "public_key": pub_hex
    })
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    
    # Check claim hash matches
    canon = canonicalize(payload)
    expected_hash = hashlib.sha256(canon).hexdigest()
    assert data["claim_hash"] == expected_hash

def test_provenance_verify_tampered():
    """Verify endpoint rejects signature mismatch."""
    priv = generate_private_key()
    pub = priv.public_key()
    pub_hex = pub.public_bytes(
        encoding=serialization.Encoding.Raw, 
        format=serialization.PublicFormat.Raw
    ).hex()
    
    payload = {"sub": "alice"}
    sig = sign_claim(payload, priv)
    
    # Tamper with payload
    tampered_payload = {"sub": "bob"}
    
    resp = client.post("/provenance/verify", json={
        "payload": tampered_payload,
        "signature": sig,
        "public_key": pub_hex
    })
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert data["reason"] == "Signature Mismatch"

def test_provenance_verify_invalid_key_format():
    """Verify endpoint handles bad key format gracefully."""
    resp = client.post("/provenance/verify", json={
        "payload": {},
        "signature": "00"*64,
        "public_key": "not-a-hex-string"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert "Invalid Key" in data["reason"]
