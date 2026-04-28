import csv
import os
from datetime import datetime, timezone
from threading import Lock

from .storage import PROJECT_ROOT, storage_path


LOG_FILE = storage_path("logs.csv")
LEGACY_LOG_FILE = os.path.join(PROJECT_ROOT, "logs.csv")
FIELDNAMES = ["username", "timestamp", "filename", "emotion", "confidence"]
_log_lock = Lock()


def _ensure_log_file() -> None:
    if not os.path.exists(LOG_FILE):
        if os.path.exists(LEGACY_LOG_FILE) and os.path.abspath(LEGACY_LOG_FILE) != os.path.abspath(LOG_FILE):
            _migrate_legacy_log_file()
            return

        with open(LOG_FILE, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
            writer.writeheader()
        return

    with open(LOG_FILE, "r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        if reader.fieldnames == FIELDNAMES:
            return

    with open(LOG_FILE, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "username": row.get("username") or "legacy",
                    "timestamp": row.get("timestamp", ""),
                    "filename": row.get("filename", ""),
                    "emotion": row.get("emotion", ""),
                    "confidence": row.get("confidence", ""),
                }
            )


def _migrate_legacy_log_file() -> None:
    with open(LEGACY_LOG_FILE, "r", newline="", encoding="utf-8") as legacy_file:
        reader = csv.DictReader(legacy_file)
        rows = list(reader)

    with open(LOG_FILE, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "username": row.get("username") or "legacy",
                    "timestamp": row.get("timestamp", ""),
                    "filename": row.get("filename", ""),
                    "emotion": row.get("emotion", ""),
                    "confidence": row.get("confidence", ""),
                }
            )


def append_prediction(username: str, filename: str, emotion: str, confidence: float) -> None:
    row = {
        "username": username,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "filename": filename,
        "emotion": emotion,
        "confidence": confidence,
    }

    with _log_lock:
        _ensure_log_file()
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
            writer.writerow(row)


def read_history(username: str, sort: str = "desc") -> list[dict]:
    with _log_lock:
        _ensure_log_file()
        with open(LOG_FILE, "r", newline="", encoding="utf-8") as csv_file:
            rows = [
                row
                for row in csv.DictReader(csv_file)
                if row.get("username") == username
            ]

    reverse = sort != "asc"
    return sorted(rows, key=lambda row: row.get("timestamp", ""), reverse=reverse)


def clear_history(username: str) -> None:
    with _log_lock:
        _ensure_log_file()
        with open(LOG_FILE, "r", newline="", encoding="utf-8") as csv_file:
            rows = [
                row
                for row in csv.DictReader(csv_file)
                if row.get("username") != username
            ]

        with open(LOG_FILE, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
