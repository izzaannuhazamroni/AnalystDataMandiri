"""Cache in-memory DataFrame bersih per dataset (LRU) agar interaksi Studio ≤ 300 ms."""
import threading
from collections import OrderedDict

import pandas as pd

from . import config, supa
from .pipeline import process_file

_lock = threading.Lock()
_cache: "OrderedDict[str, tuple[pd.DataFrame, dict, list]]" = OrderedDict()


def _key(dataset: dict) -> str:
    return f"{dataset['id']}:{dataset['file_path']}"


def put(dataset: dict, df: pd.DataFrame, types: dict, columns: list) -> None:
    with _lock:
        _cache[_key(dataset)] = (df, types, columns)
        _cache.move_to_end(_key(dataset))
        while len(_cache) > config.CACHE_SIZE:
            _cache.popitem(last=False)


def get_frame(dataset: dict) -> tuple[pd.DataFrame, dict, list]:
    k = _key(dataset)
    with _lock:
        if k in _cache:
            _cache.move_to_end(k)
            return _cache[k]
    content = supa.download(dataset["file_path"])
    df, types, columns, _ = process_file(content, dataset["file_name"])
    put(dataset, df, types, columns)
    return df, types, columns


def evict(dataset_id: str) -> None:
    with _lock:
        for k in [k for k in _cache if k.startswith(f"{dataset_id}:")]:
            _cache.pop(k, None)
