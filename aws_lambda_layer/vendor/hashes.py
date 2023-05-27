# -*- coding: utf-8 -*-

"""
Made hashlib more user friendly.

Usage::

        >>> from fixa.hashes import hashes
        >>> print(hashes.of_bytes(b"hello"))
        b1fec41621e338896e2d26f232a6b006

        >>> print(hashes.of_str("world"))
        78e731027d8fd50ed642340b7c9a63b3

        >>> print(hashes.of_file("hashes.py"))
        4cddcb5562cbff652b0e4c8a0300337a

Ref:

- hashlib: https://docs.python.org/3/library/hashlib.html
"""

import typing as T
import enum
import hashlib
from pathlib import Path


class HashAlgoEnum(str, enum.Enum):
    md5 = "md5"
    sha1 = "sha1"
    sha224 = "sha224"
    sha256 = "sha256"
    sha384 = "sha384"
    sha512 = "sha512"


class Hashes:
    """
    A hashlib wrapper class allow you to use one line to do hash as you wish.
    """

    def __init__(
        self,
        algo: HashAlgoEnum = HashAlgoEnum.md5,
        hexdigest: bool = True,
    ):
        self.algo = getattr(hashlib, algo.value)
        self.hexdigest: bool = hexdigest

    def use_md5(self) -> "Hashes":
        """
        Use md5 hash algorithm.
        """
        self.algo = getattr(hashlib, HashAlgoEnum.md5.value)
        return self

    def use_sha1(self) -> "Hashes":
        """
        Use sha1 hash algorithm.
        """
        self.algo = getattr(hashlib, HashAlgoEnum.sha1.value)
        return self

    def use_sha224(self) -> "Hashes":
        """
        Use sha224 hash algorithm.
        """
        self.algo = getattr(hashlib, HashAlgoEnum.sha224.value)
        return self

    def use_sha256(self) -> "Hashes":
        """
        Use sha256 hash algorithm.
        """
        self.algo = getattr(hashlib, HashAlgoEnum.sha256.value)
        return self

    def use_sha384(self) -> "Hashes":
        """
        Use sha384 hash algorithm.
        """
        self.algo = getattr(hashlib, HashAlgoEnum.sha384.value)
        return self

    def use_sha512(self) -> "Hashes":
        """
        Use sha512 hash algorithm.
        """
        self.algo = getattr(hashlib, HashAlgoEnum.sha512.value)
        return self

    def use_hexdigesst(self) -> "Hashes":
        """
        Return hash in hex string.
        """
        self.hexdigest = True
        return self

    def use_bytesdigest(self) -> "Hashes":
        """
        Return hash in bytes.
        """
        self.hexdigest = False
        return self

    def _construct(self, algo: T.Optional[HashAlgoEnum] = None):
        if algo is None:
            return self.algo()
        else:
            return getattr(hashlib, algo.value)()

    def _digest(self, m, hexdigest: T.Optional[bool]) -> T.Union[str, bytes]:
        if hexdigest is None:
            if self.hexdigest:
                return m.hexdigest()
            else:
                return m.digest()
        else:
            if hexdigest:
                return m.hexdigest()
            else:
                return m.digest()

    def of_str(
        self,
        s: str,
        algo: T.Optional[HashAlgoEnum] = None,
        hexdigest: T.Optional[bool] = None,
    ) -> T.Union[str, bytes]:
        """
        Return hash value of a string.
        """
        m = self._construct(algo)
        m.update(s.encode("utf-8"))
        return self._digest(m, hexdigest)

    def of_bytes(
        self,
        b: bytes,
        algo: T.Optional[HashAlgoEnum] = None,
        hexdigest: T.Optional[bool] = None,
    ) -> T.Union[str, bytes]:
        """
        Return hash value of a bytes.
        """
        m = self._construct(algo)
        m.update(b)
        return self._digest(m, hexdigest)

    def of_str_or_bytes(
        self,
        s_or_b: T.Union[bytes, str],
        algo: T.Optional[HashAlgoEnum] = None,
        hexdigest: T.Optional[bool] = None,
    ) -> T.Union[str, bytes]:
        """
        Return hash value of a bytes or string.
        """
        if isinstance(s_or_b, str):
            return self.of_str(s_or_b, algo, hexdigest)
        else:
            return self.of_bytes(s_or_b, algo, hexdigest)

    def of_file(
        self,
        abspath: T.Union[str, Path, T.Any],
        nbytes: int = 0,
        chunk_size: int = 1024,
        algo: T.Optional[HashAlgoEnum] = None,
        hexdigest: T.Optional[bool] = None,
    ) -> T.Union[str, bytes]:
        """
        Return hash value of a file, or only a piece of a file
        """
        p = Path(abspath)
        with p.open("rb") as f:
            return self.of_file_object(
                f,
                nbytes=nbytes,
                chunk_size=chunk_size,
                algo=algo,
                hexdigest=hexdigest,
            )

    def of_file_object(
        self,
        f,
        nbytes: int = 0,
        chunk_size: int = 4096,
        algo: T.Optional[HashAlgoEnum] = None,
        hexdigest: T.Optional[bool] = None,
    ) -> T.Union[str, bytes]:
        if nbytes < 0:
            raise ValueError("chunk_size cannot smaller than 0")
        if chunk_size < 1:
            raise ValueError("chunk_size cannot smaller than 1")
        if (nbytes > 0) and (nbytes < chunk_size):
            chunk_size = nbytes

        m = self._construct(algo)

        if nbytes:  # use first n bytes only
            have_reads = 0
            while True:
                have_reads += chunk_size
                if have_reads > nbytes:
                    n = nbytes - (have_reads - chunk_size)
                    if n:
                        data = f.read(n)
                        m.update(data)
                    break
                else:
                    data = f.read(chunk_size)
                    m.update(data)
        else:  # use entire content
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                m.update(data)
        return self._digest(m, hexdigest)

    def of_folder(
        self,
        abspath: T.Union[str, Path, T.Any],
        algo: T.Optional[HashAlgoEnum] = None,
        hexdigest: T.Optional[bool] = None,
    ) -> str:
        """
        Return hash value of a folder. It is based on the concatenation of
        the hash values of all files in the folder. The order of the files
        are sorted by their paths.
        """
        path = Path(abspath)
        if not path.is_dir():
            raise NotADirectoryError(f"{path} is not a folder!")
        hashes = list()
        for p in sorted(path.glob("**/*"), key=lambda x: str(x)):
            if p.is_file():
                hashes.append(self.of_file(p, algo=algo, hexdigest=hexdigest))
        return self.of_str(
            s="".join(hashes),
            algo=algo,
            hexdigest=hexdigest,
        )

    def of_paths(
        self,
        paths: T.List[T.Union[str, Path, T.Any]],
        algo: T.Optional[HashAlgoEnum] = None,
        hexdigest: T.Optional[bool] = None,
    ) -> str:
        """
        Return hash value of a list of paths. It is based on the concatenation of
        the hash values of all files and folders.
        """
        hashes = list()
        for path in paths:
            path = Path(path)
            if path.is_dir():
                hashes.append(self.of_folder(path, algo=algo, hexdigest=hexdigest))
            elif path.is_file():
                hashes.append(self.of_file(path, algo=algo, hexdigest=hexdigest))
            else:  # pragma: no cover
                pass
        return self.of_str(
            s="".join(hashes),
            algo=algo,
            hexdigest=hexdigest,
        )


hashes = Hashes()
hashes.use_sha256().use_hexdigesst()
