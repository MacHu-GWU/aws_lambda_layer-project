# -*- coding: utf-8 -*-

import typing as T


def ensure_exact_one_true(lst: T.List[bool]):
    if sum(lst) != 1:
        raise ValueError(f"Expected exactly one True, but got {lst}")
