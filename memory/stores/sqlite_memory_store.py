import json
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from memory.models.memory_category import MemoryCategory
from memory.models.memory_entry import MemoryEntry
from memory.models.memory_query import MemoryQuery
from memory.models.memory_types import (
    MemoryImportance,
    MemoryScope,
    MemorySource,
    MemoryType,
)
from memory.stores.memory_store import MemoryStore
from utils.logger import logger



class SQLiteMemoryStore(MemoryStore):
    """
    SQLite-backed implementation of the MemoryStore contract.
    """

    def __init__(self, database_path: str = "memory.db") -> None:

        self.database_path = database_path
        logger.info("Memory store initialized | database=%s",Path(self.database_path).resolve(),)
        self._initialize_database()



    def _get_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection



    def _initialize_database(self) -> None:
        with self._get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    source TEXT NOT NULL,
                    importance TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    metadata TEXT NOT NULL
                )
                """
            )

            connection.commit()



    def save(self, memory: MemoryEntry) -> None:
        with self._get_connection() as connection:
            connection.execute(
                """
                INSERT INTO memories (
                    id,
                    content,
                    category,
                    memory_type,
                    scope,
                    source,
                    importance,
                    confidence,
                    created_at,
                    updated_at,
                    expires_at,
                    metadata
                )
                VALUES (?, ?,?,?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.id,
                    memory.content,
                    memory.category.value,
                    memory.memory_type.value,
                    memory.scope.value,
                    memory.source.value,
                    memory.importance.value,
                    memory.confidence,
                    memory.created_at.isoformat(),
                    memory.updated_at.isoformat(),
                    (
                        memory.expires_at.isoformat()
                        if memory.expires_at
                        else None
                    ),
                    json.dumps(memory.metadata),
                ),
            )

            connection.commit()




    def get(self, memory_id: str) -> MemoryEntry | None:
        with self._get_connection() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM memories
                WHERE id = ?
                """,
                (memory_id,),
                 ).fetchone()

            if row is None:
                return None

        return self._row_to_memory(row)




    def search(self, query: MemoryQuery) -> list[MemoryEntry]:

        conditions = ["content LIKE ?"]

        parameters: list[object] = [f"%{query.query}%"]

        logger.info("Memory search | query=%s | scope=%s | ""minimum_confidence=%s | limit=%s",
        query.query,
        query.scope,
        query.minimum_confidence,
        query.limit,)


        if query.scope is not None:
            conditions.append("scope = ?")
            parameters.append(query.scope.value)

        if query.memory_type is not None:
            conditions.append("memory_type = ?")
            parameters.append(query.memory_type.value)

        if query.minimum_confidence is not None:
            conditions.append("confidence >= ?")
            parameters.append(query.minimum_confidence)

        if not query.include_expired:
            conditions.append("(expires_at IS NULL OR expires_at > ?)")
            parameters.append(datetime.now(timezone.utc).isoformat())

        if query.capability is not None:
            conditions.append(
                """
            (
                json_extract(metadata, '$.capability') = ?
                OR json_extract(metadata, '$.capability') = 'common'
            )
            """)
            parameters.append(query.capability)

        where_clause = " AND ".join(conditions)

        sql = f"""
            SELECT *
            FROM memories
            WHERE {where_clause}
            ORDER BY updated_at DESC
            LIMIT ?
            """

        parameters.append(query.limit)

        with self._get_connection() as connection:
                rows = connection.execute(sql,parameters,).fetchall()
                logger.info("Memory search results | count=%d",len(rows),)
        return [self._row_to_memory(row) for row in rows]




    def update(self, memory: MemoryEntry) -> None:
        with self._get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE memories
                SET
                    content = ?,
                    memory_type = ?,
                    category=?,
                    scope = ?,
                    source = ?,
                    importance = ?,
                    confidence = ?,
                    created_at = ?,
                    updated_at = ?,
                    expires_at = ?,
                    metadata = ?
                WHERE id = ?
                """,
                (
                    memory.content,
                    memory.memory_type.value,
                    memory.category.value,
                    memory.scope.value,
                    memory.source.value,
                    memory.importance.value,
                    memory.confidence,
                    memory.created_at.isoformat(),
                    memory.updated_at.isoformat(),
                    (
                        memory.expires_at.isoformat()
                        if memory.expires_at
                        else None
                    ),
                    json.dumps(memory.metadata),
                    memory.id,
                ),
            )

            if cursor.rowcount == 0:
                raise KeyError(
                    f"Memory not found: {memory.id}"
                )

            connection.commit()



    def delete(self, memory_id: str) -> None:
        with self._get_connection() as connection:
            connection.execute(
                """
                DELETE FROM memories
                WHERE id = ?
                """,
                (memory_id,),
            )

            connection.commit()




    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(
            id=row["id"],
            content=row["content"],
            category=MemoryCategory(row["category"]),
            memory_type=MemoryType(row["memory_type"]),
            scope=MemoryScope(row["scope"]),
            source=MemorySource(row["source"]),
            importance=MemoryImportance(row["importance"]),
            confidence=row["confidence"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            expires_at=(
                datetime.fromisoformat(row["expires_at"])
                if row["expires_at"]
                else None
            ),
            metadata=json.loads(row["metadata"]),
        )



    def list(self,query: MemoryQuery,) -> list[MemoryEntry]:

        conditions = []

        parameters: list[object] = []

        if query.scope is not None:
            conditions.append("scope = ?")
            parameters.append(query.scope.value)

        if query.memory_type is not None:
            conditions.append("memory_type = ?")
            parameters.append(query.memory_type.value)

        if query.category is not None:
            conditions.append("category = ?")
            parameters.append(query.category.value)

        if query.capability is not None:
            conditions.append(
            """
            (
            json_extract(metadata, '$.capability') = ?
            OR json_extract(metadata, '$.capability') = 'common'
            )
            """)
            parameters.append(query.capability)

        if query.minimum_confidence is not None:
            conditions.append("confidence >= ?")
            parameters.append(query.minimum_confidence)

        if not query.include_expired:
            conditions.append("(expires_at IS NULL OR expires_at > ?)")
            parameters.append(datetime.now(timezone.utc).isoformat())

        where_clause = (
            f"WHERE {' AND '.join(conditions)}"
            if conditions
            else ""
        )

        sql = f"""
            SELECT *
            FROM memories
            {where_clause}
            ORDER BY updated_at DESC
            LIMIT ?
        """

        parameters.append(query.limit)

        with self._get_connection() as connection:
            rows = connection.execute(
                sql,
                parameters,
            ).fetchall()

        return [
            self._row_to_memory(row)
            for row in rows
        ]