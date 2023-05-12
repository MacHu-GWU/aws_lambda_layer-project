# -*- coding: utf-8 -*-


import hashlib


def sha256_of_bytes(b: bytes) -> str:
    sha256 = hashlib.sha256()
    sha256.update(b)
    return sha256.hexdigest()
