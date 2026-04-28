import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from threading import Lock

from passlib.context import CryptContext

from .storage import PROJECT_ROOT, storage_path


BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = storage_path("database.db")
LEGACY_DB_FILES = [
    os.path.join(BACKEND_DIR, "database.db"),
    os.path.join(PROJECT_ROOT, "users.db"),
]
PBKDF2_ITERATIONS = 260_000
password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
_db_lock = Lock()


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _db_lock:
        with _connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(username) REFERENCES users(username)
                )
                """
            )
            user_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if user_count == 0:
                _migrate_legacy_databases(connection)


def _migrate_legacy_databases(connection: sqlite3.Connection) -> None:
    for legacy_db_file in LEGACY_DB_FILES:
        if os.path.abspath(legacy_db_file) == os.path.abspath(DB_FILE):
            continue
        if not os.path.exists(legacy_db_file):
            continue

        with sqlite3.connect(legacy_db_file) as legacy:
            legacy.row_factory = sqlite3.Row
            users = legacy.execute(
                "SELECT username, password_hash, created_at FROM users"
            ).fetchall()
            sessions = legacy.execute(
                "SELECT token, username, created_at FROM sessions"
            ).fetchall()

        connection.executemany(
            "INSERT OR IGNORE INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            [(row["username"], row["password_hash"], row["created_at"]) for row in users],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO sessions (token, username, created_at) VALUES (?, ?, ?)",
            [(row["token"], row["username"], row["created_at"]) for row in sessions],
        )

        migrated_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if migrated_count > 0:
            return


def _hash_legacy_password(password: str, salt: str) -> str:
    password_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS,
    )
    return password_key.hex()


def _hash_password(password: str) -> str:
    return password_context.hash(password)


def _verify_legacy_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored_hash.split("$")
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256" or int(iterations) != PBKDF2_ITERATIONS:
        return False

    actual = _hash_legacy_password(password, salt)
    return hmac.compare_digest(actual, expected)


def _verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("pbkdf2_sha256$"):
        return _verify_legacy_password(password, stored_hash)
    return password_context.verify(password, stored_hash)


def create_user(username: str, password: str) -> bool:
    username = username.strip()
    password_hash = _hash_password(password)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with _db_lock:
        try:
            with _connect() as connection:
                connection.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                    (username, password_hash, created_at),
                )
            return True
        except sqlite3.IntegrityError:
            return False


def authenticate_user(username: str, password: str) -> bool:
    with _db_lock:
        with _connect() as connection:
            row = connection.execute(
                "SELECT password_hash FROM users WHERE username = ?",
                (username.strip(),),
            ).fetchone()

    return bool(row and _verify_password(password, row["password_hash"]))


def create_session(username: str) -> str:
    token = secrets.token_urlsafe(32)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with _db_lock:
        with _connect() as connection:
            connection.execute(
                "INSERT INTO sessions (token, username, created_at) VALUES (?, ?, ?)",
                (token, username.strip(), created_at),
            )

    return token


def get_session_user(token: str) -> str | None:
    with _db_lock:
        with _connect() as connection:
            row = connection.execute(
                "SELECT username FROM sessions WHERE token = ?",
                (token,),
            ).fetchone()

    return row["username"] if row else None


def delete_session(token: str) -> None:
    with _db_lock:
        with _connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token = ?", (token,))


init_db()
