import hashlib
import uuid


def uuid_from_ints(first_id: int, second_id: int) -> str:
    """This is an aligned implementation with a sql function. Do not change."""

    # Create hash of the two IDs concatenated with comma
    hash_input = f"{first_id},{second_id}".encode("utf-8")
    hex_string = hashlib.sha256(hash_input).hexdigest()

    # Format the hash as a UUID string
    uuid_str = f"{hex_string[:8]}-{hex_string[8:12]}-{hex_string[12:16]}-{hex_string[16:20]}-{hex_string[20:32]}"

    return uuid.UUID(uuid_str)
