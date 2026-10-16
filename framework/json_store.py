"""Atomic JSON file store: spin-lock on a lockfile + temp-file replace.
Simulates one-service-one-DB local consistency."""
import json
import os
import tempfile
import time
import contextlib


class JsonStore:
    def __init__(self, path: str):
        self.path = path
        self.lock_path = path + ".lock"
        if not os.path.exists(path):
            self._write({"seq": 0, "rows": {}})

    def _read(self):
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data):
        d = os.path.dirname(self.path) or "."
        fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    @contextlib.contextmanager
    def write(self):
        # cross-process lock: spin on creating the lock file exclusively
        while True:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                break
            except FileExistsError:
                time.sleep(0.01)
        try:
            data = self._read()
            yield data
            self._write(data)
        finally:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)

    def read(self):
        return self._read()

    def next_id(self, data, prefix="id"):
        data["seq"] += 1
        return f"{prefix}_{data['seq']:06d}"
