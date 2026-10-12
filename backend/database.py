import sqlite3
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "netwatch.db"


def get_connection():
    """Open a connection to the NetWatch SQLite database."""

    DATA_DIR.mkdir(exist_ok=True)

    return sqlite3.connect(DATABASE_PATH)


def initialize_database():
    """Create the database tables if they do not already exist."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TEXT NOT NULL,
                check_type TEXT NOT NULL,
                target TEXT NOT NULL,
                is_healthy INTEGER NOT NULL,
                latency_ms REAL,
                packet_loss REAL,
                details TEXT
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_measurements_recorded_at
            ON measurements(recorded_at)
            """
        )


def save_measurement(
    check_type,
    target,
    is_healthy,
    latency_ms=None,
    packet_loss=None,
    details=None,
):
    """Save one network health measurement."""

    recorded_at = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO measurements (
                recorded_at,
                check_type,
                target,
                is_healthy,
                latency_ms,
                packet_loss,
                details
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recorded_at,
                check_type,
                target,
                int(is_healthy),
                latency_ms,
                packet_loss,
                details,
            ),
        )


def get_recent_measurements(limit=10):
    """Return the most recently stored measurements."""

    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT
                recorded_at,
                check_type,
                target,
                is_healthy,
                latency_ms,
                packet_loss,
                details
            FROM measurements
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

        return cursor.fetchall()