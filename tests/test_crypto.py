"""
Tests for cns_py.crypto.
"""
import json
import pytest
from cns_py.crypto import canonicalize, generate_private_key, sign_claim, verify_claim, load_private_key, load_public_key
from cryptography.hazmat.primitives import serialization

def test_canonicalize_ordering():
    """Canonicalization must sort keys."""
    d1 = {"b": 2, "a": 1}
    d2 = {"a": 1, "b": 2}
    
    c1 = canonicalize(d1)
    c2 = canonicalize(d2)
    
    assert c1 == c2
    # Expected: {"a":1,"b":2} (no spaces)
    assert c1 == b'{"a":1,"b":2}'

def test_canonicalize_types():
    """Handles nested types."""
    d = {
        "list": [3, 2, 1],
        "nested": {"z": 9, "y": 8}
    }
    c = canonicalize(d)
    # Lists are NOT sorted (arrays order matters), dicts are.
    # {"list":[3,2,1],"nested":{"y":8,"z":9}}
    expected = b'{"list":[3,2,1],"nested":{"y":8,"z":9}}'
    assert c == expected

def test_canonicalize_utf8():
    """Handles verified UTF-8."""
    # "ñ" is \u00f1 (2 bytes in utf-8: 0xC3 0xB1)
    # JCS requires Raw UTF-8 bytes, not escaped \u00f1
    d = {"val": "ñ"}
    c = canonicalize(d)
    # b'{"val":"\xc3\xb1"}'
    expected_str = '{"val":"ñ"}'
    assert c.decode('utf-8') == expected_str

def test_sign_verify_roundtrip():
    """Happy path signing."""
    priv = generate_private_key()
    pub = priv.public_key()
    
    claim = {"sub": "alice", "op": "write"}
    
    sig = sign_claim(claim, priv)
    assert len(sig) == 128 # 64 bytes hex
    
    valid = verify_claim(claim, sig, pub)
    assert valid is True

def test_verify_tamper():
    """Signature fails if data changes."""
    priv = generate_private_key()
    pub = priv.public_key()
    
    claim = {"sub": "alice"}
    sig = sign_claim(claim, priv)
    
    tampered = {"sub": "bob"}
    valid = verify_claim(tampered, sig, pub)
    assert valid is False

def test_verify_reordering_is_safe():
    """Data reordering shouldn't matter if logic is same (canonicalization handles it)."""
    priv = generate_private_key()
    pub = priv.public_key()
    
    claim1 = {"a": 1, "b": 2}
    sig = sign_claim(claim1, priv)
    
    # claim2 has different key order in python dict definition
    claim2 = {"b": 2, "a": 1}
    
    # Should still verify
    valid = verify_claim(claim2, sig, pub)
    assert valid is True

def test_key_loading():
    """Test hex loading helpers."""
    priv = generate_private_key()
    
    # Export raw seed
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    seed_hex = priv_bytes.hex()
    
    # Reload
    loaded_priv = load_private_key(seed_hex)
    
    # Check if they produce same sig
    msg = {"test": 1}
    sig1 = sign_claim(msg, priv)
    sig2 = sign_claim(msg, loaded_priv)
    assert sig1 == sig2
