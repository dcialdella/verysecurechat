import logging
import time
from typing import Any

import gnupg

logger = logging.getLogger(__name__)


def create_gpg() -> gnupg.GPG:
    return gnupg.GPG()


def is_valid_key(key: dict[str, Any]) -> bool:
    if key.get("expired", False) or key.get("revoked", False):
        return False
    expires = key.get("expires", "")
    if expires and expires.isdigit():
        if int(expires) < time.time():
            return False
    return True


def list_public_keys(gpg_instance: gnupg.GPG) -> list[dict[str, Any]]:
    return gpg_instance.list_keys()


def list_private_keys(gpg_instance: gnupg.GPG) -> list[dict[str, Any]]:
    return gpg_instance.list_keys(True)


def get_valid_sorted_keys(
    gpg_instance: gnupg.GPG, private: bool = False
) -> list[dict[str, Any]]:
    keys = gpg_instance.list_keys(private)
    valid = [k for k in keys if is_valid_key(k)]
    return sorted(valid, key=lambda k: k.get("uids", [""])[0], reverse=True)


def encrypt_message(
    gpg_instance: gnupg.GPG,
    message: str,
    recipient_key: str,
    always_trust: bool = True,
) -> Any:
    return gpg_instance.encrypt(message, recipient_key, always_trust=always_trust)


def decrypt_message(
    gpg_instance: gnupg.GPG,
    encrypted_bytes: bytes,
    extra_args: list[str] | None = None,
) -> Any:
    result = gpg_instance.decrypt(encrypted_bytes, extra_args=extra_args or [])
    if not result.ok:
        logger.debug("Decrypt failed: %s", result.status)
    return result
