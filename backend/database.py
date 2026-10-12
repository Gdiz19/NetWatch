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
    """Create the NetWatch database tables."""

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

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS outages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                duration_seconds REAL
            )
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
    """Return recently stored measurements."""

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


def get_open_outage():
    """Return the current unresolved outage, if one exists."""

    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT id, started_at
            FROM outages
            WHERE ended_at IS NULL
            ORDER BY id DESC
            LIMIT 1
            """
        )

        return cursor.fetchone()


def start_outage():
    """Start an outage unless one is already open."""

    existing_outage = get_open_outage()

    if existing_outage:
        return existing_outage[0]

    started_at = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO outages (
                started_at
            )
            VALUES (?)
            """,
            (started_at,),
        )

        return cursor.lastrowid


def end_outage():
    """Resolve the currently open outage."""

    outage = get_open_outage()

    if outage is None:
        return None

    outage_id, started_at_text = outage

    ended_at = datetime.now().astimezone()
    started_at = datetime.fromisoformat(started_at_text)

    duration_seconds = (
        ended_at - started_at
    ).total_seconds()

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE outages
            SET
                ended_at = ?,
                duration_seconds = ?
            WHERE id = ?
            """,
            (
                ended_at.isoformat(timespec="seconds"),
                duration_seconds,
                outage_id,
            ),
        )

    return {
        "id": outage_id,
        "started_at": started_at_text,
        "ended_at": ended_at.isoformat(timespec="seconds"),
        "duration_seconds": duration_seconds,
    }


def get_recent_outages(limit=5):
    """Return recent outage history."""

    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT
                id,
                started_at,
                ended_at,
                duration_seconds
            FROM outages
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

        return cursor.fetchall()

def get_latest_measurement(check_type):
    """Return the newest measurement for a given check type."""

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
            WHERE check_type = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (check_type,),
        )

        return cursor.fetchone()


def get_measurement_count():
    """Return the total number of stored measurements."""

    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT COUNT(*)
            FROM measurements
            """
        )

        return cursor.fetchone()[0]