import hashlib


def hash_email(email: str, salt: str) -> str:
    """
    Hash an email address using SHA-256 with salt from environment.
    """
    if not salt:
        raise ValueError("salt must have some contents")

    normalized = email.lower().strip()

    hasher = hashlib.sha256()
    hasher.update(salt.encode("utf-8"))
    hasher.update(normalized.encode("utf-8"))
    return hasher.digest().hex()
