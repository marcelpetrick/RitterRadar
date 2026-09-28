# SPDX-License-Identifier: GPL-3.0-or-later
"""Private files and crash-safe, cross-platform database ownership."""

import os
import sqlite3
from pathlib import Path


def private_file(path: Path) -> None:
    if path.exists():
        path.chmod(0o600)


class InstanceLock:
    """Hold an exclusive SQLite transaction in a separate lock database.

    OS file locks release on process death; the application database stays
    available for backups and reads. All application starts must take this lock.
    """

    def __init__(self, path: Path) -> None:
        self.connection: sqlite3.Connection | None = None
        if str(path) == ":memory:":
            return
        os.umask(0o077)
        created = not path.parent.exists()
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if created or path.parent.resolve() == Path("data").resolve():
            path.parent.chmod(0o700)
        lock_path = path.with_suffix(path.suffix + ".instance")
        connection = sqlite3.connect(lock_path, timeout=0)
        private_file(lock_path)
        try:
            connection.execute("BEGIN EXCLUSIVE")
        except sqlite3.OperationalError:
            connection.close()
            raise RuntimeError("Another RitterRadar instance owns this database") from None
        self.connection = connection
        for file in (path, Path(str(path) + "-wal"), Path(str(path) + "-shm")):
            private_file(file)

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
