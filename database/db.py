
import sqlite3
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "sentinelguard.db"

DATABASE_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                track_id INTEGER,
                person_name TEXT,
                similarity REAL,
                timestamp TEXT NOT NULL,
                evidence_path TEXT,
                description TEXT
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_security_events_timestamp
            ON security_events(timestamp)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_security_events_type
            ON security_events(event_type)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_security_events_track
            ON security_events(track_id)
        """)

    print("SentinelGuard database initialized.")
    print("Database:", DATABASE_PATH)


def create_event(
    event_type,
    track_id=None,
    person_name=None,
    similarity=None,
    evidence_path=None,
    description=None
):
    timestamp = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO security_events (
                event_type,
                track_id,
                person_name,
                similarity,
                timestamp,
                evidence_path,
                description
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_type,
            track_id,
            person_name,
            similarity,
            timestamp,
            str(evidence_path) if evidence_path else None,
            description
        ))

        return cursor.lastrowid


def _build_event_filters(
    event_type=None,
    date_from=None,
    date_to=None,
    search=None
):
    conditions = []
    parameters = []

    if event_type:
        conditions.append("event_type = ?")
        parameters.append(event_type)

    if date_from:
        conditions.append("substr(timestamp, 1, 10) >= ?")
        parameters.append(date_from)

    if date_to:
        conditions.append("substr(timestamp, 1, 10) <= ?")
        parameters.append(date_to)

    if search:
        search_term = f"%{search.strip()}%"
        conditions.append("""
            (
                COALESCE(person_name, '') LIKE ?
                OR CAST(COALESCE(track_id, '') AS TEXT) LIKE ?
                OR COALESCE(description, '') LIKE ?
                OR CAST(id AS TEXT) LIKE ?
            )
        """)
        parameters.extend([
            search_term,
            search_term,
            search_term,
            search_term
        ])

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    return where_clause, parameters


def search_events(
    event_type=None,
    date_from=None,
    date_to=None,
    search=None,
    page=1,
    page_size=20
):
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 100))
    offset = (page - 1) * page_size

    where_clause, parameters = _build_event_filters(
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
        search=search
    )

    with get_connection() as connection:
        total = connection.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM security_events
            {where_clause}
            """,
            parameters
        ).fetchone()["total"]

        rows = connection.execute(
            f"""
            SELECT *
            FROM security_events
            {where_clause}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            parameters + [page_size, offset]
        ).fetchall()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "events": [dict(row) for row in rows]
    }


def get_event_by_id(event_id):
    with get_connection() as connection:
        row = connection.execute("""
            SELECT *
            FROM security_events
            WHERE id = ?
        """, (event_id,)).fetchone()

    return dict(row) if row else None


def get_events(limit=100):
    limit = max(1, min(int(limit), 500))

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT *
            FROM security_events
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

    return [dict(row) for row in rows]


def get_event_count():
    with get_connection() as connection:
        row = connection.execute("""
            SELECT COUNT(*) AS total
            FROM security_events
        """).fetchone()

    return row["total"]


def get_event_counts_by_type():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT event_type, COUNT(*) AS total
            FROM security_events
            GROUP BY event_type
        """).fetchall()

    return {
        row["event_type"]: row["total"]
        for row in rows
    }
