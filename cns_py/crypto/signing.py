"""
Signing and Verification using Ed25519.
"""
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .canonical import canonicalize


def generate_private_key() -> Ed25519PrivateKey:
    """Generate a new Ed25519 private key."""
    return Ed25519PrivateKey.generate()

def load_private_key(hex_seed: str) -> Ed25519PrivateKey:
    """Load a private key from a hex-encoded 32-byte seed.
    Note: Ed25519PrivateKey.from_private_bytes takes 32 bytes.
    """
    # If using full key serialization formats (PKCS8/OpenSSH), use
    # serialization.load_pem_private_key.
    # For raw seeds:
    seed_bytes = bytes.fromhex(hex_seed)
    return Ed25519PrivateKey.from_private_bytes(seed_bytes)

def load_public_key(hex_key: str) -> Ed25519PublicKey:
    """Load a public key from hex bytes."""
    key_bytes = bytes.fromhex(hex_key)
    return Ed25519PublicKey.from_public_bytes(key_bytes)

def sign_claim(claim_payload: Any, private_key: Ed25519PrivateKey) -> str:
    """
    Canonicalize the payload and sign it.
    Returns the signature as a hex string.
    """
    data_bytes = canonicalize(claim_payload)
    signature_bytes = private_key.sign(data_bytes)
    return signature_bytes.hex()

def verify_claim(claim_payload: Any, signature_hex: str, public_key: Ed25519PublicKey) -> bool:
    """
    Verify that the signature matches the canonical payload and public key.
    """
    data_bytes = canonicalize(claim_payload)
    signature_bytes = bytes.fromhex(signature_hex)
    try:
        public_key.verify(signature_bytes, data_bytes)
        return True
    except Exception:
        return False
