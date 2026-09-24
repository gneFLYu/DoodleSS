"""Disposable private wire cache; never a source of editable mathematical state."""
from __future__ import annotations

import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


class ProjectResponseCache:
    MAX_BYTES = 64 * 1024 * 1024

    def __init__(self, backend_root: Path, directory: Path | None = None):
        self.root = backend_root.resolve()
        user_suffix = f"-{os.getuid()}" if hasattr(os, "getuid") else ""
        self.directory = directory or Path(tempfile.gettempdir()) / ("hfpss-studio-response-cache" + user_suffix)
        def dependency(name):
            try:
                return name, version(name)
            except PackageNotFoundError:
                return name, None
        self.runtime = (sys.version, sys.implementation.cache_tag,
                        *(dependency(name) for name in ("flask", "werkzeug", "jinja2", "sympy")))
        # A non-reloading process may still run old imported code after a file
        # edit. Such a process must neither consume nor publish a new-code cache.
        try:
            self.loaded_code = self._code_digest()
        except OSError:
            self.loaded_code = None

    @staticmethod
    def _digest_files(paths) -> str:
        digest = hashlib.sha256()
        for path in sorted(set(paths)):
            digest.update(str(path.resolve()).encode("utf-8"))
            digest.update(b"\0")
            with path.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(block)
            digest.update(b"\0")
        return digest.hexdigest()

    def _code_digest(self) -> str:
        return self._digest_files(self.root.rglob("*.py"))

    def key(self, data_path: Path) -> str | None:
        try:
            if not isinstance(data_path, Path) or not data_path.is_file():
                return None
            if self.loaded_code is None or self._code_digest() != self.loaded_code:
                return None
            # Preserve all source inputs, including archive data referenced by
            # a future migration. Content hashes also detect equal-size edits
            # whose timestamp was preserved by an editor or file synchronizer.
            data = self._digest_files([data_path, *(self.root / "data").rglob("*.json")])
            return hashlib.sha256(json.dumps(("wire-v1", self.runtime, self.loaded_code, data),
                                             separators=(",", ":")).encode()).hexdigest()
        except (OSError, ValueError):
            return None

    def _path(self, data_path: Path) -> Path:
        name = hashlib.sha256(str(data_path.resolve()).encode("utf-8")).hexdigest()
        return self.directory / (name + ".json.gz.cache")

    def _private_directory(self, *, create: bool = False) -> bool:
        if create:
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.directory.lstat()
        if not stat.S_ISDIR(info.st_mode):
            return False  # Never follow a pre-created symlink.
        return (os.name == "nt" or (info.st_uid == os.getuid() and not info.st_mode & 0o077))

    def read(self, data_path: Path, key: str) -> bytes | None:
        try:
            if not self._private_directory():
                return None
            with self._path(data_path).open("rb") as source:
                header = source.readline(8193)
                if len(header) > 8192 or not header.endswith(b"\n"):
                    return None
                metadata = json.loads(header)
                if not isinstance(metadata, dict) or metadata.get("key") != key:
                    return None
                body = source.read(self.MAX_BYTES + 1)
            if (len(body) > self.MAX_BYTES or metadata.get("bytes") != len(body)
                    or not body.startswith(b"\x1f\x8b")
                    or metadata.get("sha256") != hashlib.sha256(body).hexdigest()):
                return None
            return body
        except (OSError, ValueError, TypeError):
            return None

    def write(self, data_path: Path, key: str, body: bytes) -> None:
        if len(body) > self.MAX_BYTES:
            return
        temporary = None
        try:
            # User temp on Windows inherits the user's private ACL; POSIX gets
            # an owner-only directory and NamedTemporaryFile's owner-only file.
            if not self._private_directory(create=True):
                return
            header = json.dumps({"key": key, "bytes": len(body),
                                 "sha256": hashlib.sha256(body).hexdigest()}).encode() + b"\n"
            with tempfile.NamedTemporaryFile(dir=self.directory, suffix=".tmp", delete=False) as target:
                temporary = Path(target.name)
                target.write(header)
                target.write(body)
            os.replace(temporary, self._path(data_path))
        except OSError:
            pass  # Optional acceleration must never prevent loading a project.
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
