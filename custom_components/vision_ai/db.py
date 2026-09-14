"""SQLite database operations for Vision AI detections."""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DB_FILENAME, LOGGER

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    camera TEXT NOT NULL,
    area TEXT NOT NULL,
    det_type TEXT NOT NULL,
    people_count INTEGER NOT NULL DEFAULT 0,
    vehicle_count INTEGER NOT NULL DEFAULT 0,
    animal_count INTEGER NOT NULL DEFAULT 0,
    detected_objects TEXT,
    analysis_text TEXT,
    snapshot_path TEXT
);
"""

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_detections_ts_cam_type
    ON detections (timestamp, camera, det_type);
"""


class VisionAIDatabase:
    """Manage the Vision AI SQLite database."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the database wrapper."""
        self._hass = hass
        self._db_path = Path(hass.config.path(DB_FILENAME))
        self._conn: sqlite3.Connection | None = None

    async def async_setup(self) -> None:
        """Create tables and indexes if they don't exist."""
        await self._hass.async_add_executor_job(self._setup_db)
        LOGGER.info("Vision AI database ready at %s", self._db_path)

    def _setup_db(self) -> None:
        """Synchronous database setup."""
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(CREATE_TABLE)
        conn.execute(CREATE_INDEX)
        conn.commit()
        conn.close()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a connection (creates one per-thread for safety)."""
        return sqlite3.connect(str(self._db_path))

    async def async_record_detection(self, data: dict[str, Any]) -> int:
        """Insert a detection record and return the row ID."""
        return await self._hass.async_add_executor_job(
            self._record_detection, data
        )

    def _record_detection(self, data: dict[str, Any]) -> int:
        """Synchronous insert."""
        conn = self._get_conn()
        try:
            cursor = conn.execute(
                """
                INSERT INTO detections
                    (timestamp, camera, area, det_type, people_count,
                     vehicle_count, animal_count, detected_objects,
                     analysis_text, snapshot_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.get("timestamp", ""),
                    data.get("camera", ""),
                    data.get("area", ""),
                    data.get("det_type", ""),
                    int(data.get("people_count", 0)),
                    int(data.get("vehicle_count", 0)),
                    int(data.get("animal_count", 0)),
                    data.get("detected_objects") or "",
                    data.get("analysis_text", ""),
                    data.get("snapshot_path", ""),
                ),
            )
            conn.commit()
            row_id = cursor.lastrowid
            LOGGER.debug("Recorded detection id=%s for %s", row_id, data.get("area"))
            return row_id
        finally:
            conn.close()

    async def async_query_detections(
        self,
        camera: str | None = None,
        det_type: str | None = None,
        hours: int = 24,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query recent detections with optional filters."""
        return await self._hass.async_add_executor_job(
            self._query_detections, camera, det_type, hours, limit
        )

    def _query_detections(
        self,
        camera: str | None,
        det_type: str | None,
        hours: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Synchronous query."""
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row
            sql = "SELECT * FROM detections WHERE timestamp >= datetime('now', ?)"
            params: list[Any] = [f"-{hours} hours"]

            if camera:
                sql += " AND camera = ?"
                params.append(camera)
            if det_type:
                sql += " AND det_type = ?"
                params.append(det_type)

            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(min(limit, 1000))

            rows = conn.execute(sql, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    async def async_get_stats(
        self, hours: int = 24
    ) -> dict[str, Any]:
        """Get summary statistics for the given time window."""
        return await self._hass.async_add_executor_job(self._get_stats, hours)

    def _get_stats(self, hours: int) -> dict[str, Any]:
        """Synchronous stats query."""
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total_detections,
                    SUM(people_count) as total_people,
                    SUM(vehicle_count) as total_vehicles,
                    SUM(animal_count) as total_animals
                FROM detections
                WHERE timestamp >= datetime('now', ?)
                """,
                (f"-{hours} hours",),
            ).fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()
