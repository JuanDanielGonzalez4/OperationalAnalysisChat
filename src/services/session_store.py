import aiosqlite
from datetime import datetime, timezone

DB_PATH = "data/sessions.db"


class SessionStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def init_db(self) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_active TEXT NOT NULL
                )
                """
            )
            await db.commit()

    async def get_or_create(self, session_id: str, first_message: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            )
            row = await cursor.fetchone()

            if row is None:
                title = first_message[:80].strip()
                await db.execute(
                    "INSERT INTO sessions (session_id, title, created_at, last_active) VALUES (?, ?, ?, ?)",
                    (session_id, title, now, now),
                )
                await db.commit()
                return {
                    "session_id": session_id,
                    "title": title,
                    "created_at": now,
                    "last_active": now,
                }
            else:
                await db.execute(
                    "UPDATE sessions SET last_active = ? WHERE session_id = ?",
                    (now, session_id),
                )
                await db.commit()
                return dict(row)

    async def list_sessions(self) -> list[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM sessions ORDER BY last_active DESC"
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get(self, session_id: str) -> dict | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def delete(self, session_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM sessions WHERE session_id = ?", (session_id,)
            )
            await db.commit()
            return cursor.rowcount > 0
