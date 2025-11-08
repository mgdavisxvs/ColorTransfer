"""
PersistenceLogger Module
========================

Persistence and logging for color transfer operations.

Responsibilities:
- Log all transfer operations with metadata
- Store performance metrics and configurations
- Support querying historical runs
- Enable reproducibility and auditing

Design Principles:
- Protocol Pattern: Abstract interface for multiple backends
- Repository Pattern: Clean data access layer
- Single Responsibility: Logging only, no business logic
"""

import sqlite3
import json
from typing import Protocol, Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
import uuid


@dataclass
class TransferRun:
    """Record of a single transfer operation."""
    run_id: str
    timestamp: str
    source_hash: str
    target_hash: str
    result_hash: str
    algorithm: str
    config_json: str
    metrics_json: str
    interface_type: str
    success: bool = True
    error_message: Optional[str] = None


class AbstractPersistence(Protocol):
    """
    Abstract interface for persistence backends.

    This protocol defines the contract that all persistence implementations
    must fulfill, enabling easy swapping of backends (SQLite, PostgreSQL,
    MongoDB, etc.).
    """

    def log_run(self, run: TransferRun) -> None:
        """
        Log a transfer run.

        Parameters:
        ----------
        run : TransferRun
            Transfer run data to persist
        """
        ...

    def get_run(self, run_id: str) -> Optional[TransferRun]:
        """
        Retrieve a specific run by ID.

        Parameters:
        ----------
        run_id : str
            Unique run identifier

        Returns:
        -------
        TransferRun | None
            Run data if found, None otherwise
        """
        ...

    def list_runs(
        self,
        limit: int = 100,
        algorithm: Optional[str] = None,
        interface_type: Optional[str] = None
    ) -> List[TransferRun]:
        """
        List recent runs with optional filtering.

        Parameters:
        ----------
        limit : int
            Maximum number of runs to return
        algorithm : str, optional
            Filter by algorithm
        interface_type : str, optional
            Filter by interface type (CLI, API, WebUI)

        Returns:
        -------
        List[TransferRun]
            List of matching runs
        """
        ...

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get aggregate statistics across all runs.

        Returns:
        -------
        Dict[str, Any]
            Statistics including total runs, avg execution time, etc.
        """
        ...


class SQLitePersistence:
    """
    SQLite implementation of persistence layer.

    Stores transfer runs in a local SQLite database for lightweight,
    serverless persistence ideal for local development and single-user
    deployments.
    """

    DEFAULT_DB_PATH = "transfer_log.db"
    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize SQLite persistence.

        Parameters:
        ----------
        db_path : str, optional
            Path to SQLite database file. Uses default if None.
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create transfer_runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfer_runs (
                run_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                target_hash TEXT NOT NULL,
                result_hash TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                config_json TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                interface_type TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 1,
                error_message TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indices for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON transfer_runs(timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_algorithm
            ON transfer_runs(algorithm)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_interface_type
            ON transfer_runs(interface_type)
        """)

        # Create metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Store schema version
        cursor.execute("""
            INSERT OR REPLACE INTO metadata (key, value)
            VALUES ('schema_version', ?)
        """, (str(self.SCHEMA_VERSION),))

        conn.commit()
        conn.close()

    def log_run(self, run: TransferRun) -> None:
        """
        Log a transfer run to database.

        Parameters:
        ----------
        run : TransferRun
            Transfer run data to persist
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO transfer_runs (
                run_id, timestamp, source_hash, target_hash, result_hash,
                algorithm, config_json, metrics_json, interface_type,
                success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run.run_id,
            run.timestamp,
            run.source_hash,
            run.target_hash,
            run.result_hash,
            run.algorithm,
            run.config_json,
            run.metrics_json,
            run.interface_type,
            1 if run.success else 0,
            run.error_message
        ))

        conn.commit()
        conn.close()

    def get_run(self, run_id: str) -> Optional[TransferRun]:
        """
        Retrieve a specific run by ID.

        Parameters:
        ----------
        run_id : str
            Unique run identifier

        Returns:
        -------
        TransferRun | None
            Run data if found, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT run_id, timestamp, source_hash, target_hash, result_hash,
                   algorithm, config_json, metrics_json, interface_type,
                   success, error_message
            FROM transfer_runs
            WHERE run_id = ?
        """, (run_id,))

        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return TransferRun(
            run_id=row['run_id'],
            timestamp=row['timestamp'],
            source_hash=row['source_hash'],
            target_hash=row['target_hash'],
            result_hash=row['result_hash'],
            algorithm=row['algorithm'],
            config_json=row['config_json'],
            metrics_json=row['metrics_json'],
            interface_type=row['interface_type'],
            success=bool(row['success']),
            error_message=row['error_message']
        )

    def list_runs(
        self,
        limit: int = 100,
        algorithm: Optional[str] = None,
        interface_type: Optional[str] = None
    ) -> List[TransferRun]:
        """
        List recent runs with optional filtering.

        Parameters:
        ----------
        limit : int
            Maximum number of runs to return
        algorithm : str, optional
            Filter by algorithm
        interface_type : str, optional
            Filter by interface type

        Returns:
        -------
        List[TransferRun]
            List of matching runs
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query with optional filters
        query = """
            SELECT run_id, timestamp, source_hash, target_hash, result_hash,
                   algorithm, config_json, metrics_json, interface_type,
                   success, error_message
            FROM transfer_runs
            WHERE 1=1
        """
        params = []

        if algorithm:
            query += " AND algorithm = ?"
            params.append(algorithm)

        if interface_type:
            query += " AND interface_type = ?"
            params.append(interface_type)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            TransferRun(
                run_id=row['run_id'],
                timestamp=row['timestamp'],
                source_hash=row['source_hash'],
                target_hash=row['target_hash'],
                result_hash=row['result_hash'],
                algorithm=row['algorithm'],
                config_json=row['config_json'],
                metrics_json=row['metrics_json'],
                interface_type=row['interface_type'],
                success=bool(row['success']),
                error_message=row['error_message']
            )
            for row in rows
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get aggregate statistics across all runs.

        Returns:
        -------
        Dict[str, Any]
            Statistics including total runs, avg execution time, etc.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total runs
        cursor.execute("SELECT COUNT(*) FROM transfer_runs")
        total_runs = cursor.fetchone()[0]

        # Runs by algorithm
        cursor.execute("""
            SELECT algorithm, COUNT(*) as count
            FROM transfer_runs
            GROUP BY algorithm
        """)
        by_algorithm = {row[0]: row[1] for row in cursor.fetchall()}

        # Runs by interface
        cursor.execute("""
            SELECT interface_type, COUNT(*) as count
            FROM transfer_runs
            GROUP BY interface_type
        """)
        by_interface = {row[0]: row[1] for row in cursor.fetchall()}

        # Success rate
        cursor.execute("""
            SELECT
                SUM(success) as successful,
                COUNT(*) as total
            FROM transfer_runs
        """)
        row = cursor.fetchone()
        success_rate = (row[0] / row[1] * 100) if row[1] > 0 else 0

        # Average execution time (extract from metrics_json)
        cursor.execute("SELECT metrics_json FROM transfer_runs WHERE success = 1")
        execution_times = []
        for row in cursor.fetchall():
            try:
                metrics = json.loads(row[0])
                if 'execution_time_ms' in metrics:
                    execution_times.append(metrics['execution_time_ms'])
            except:
                pass

        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0

        conn.close()

        return {
            'total_runs': total_runs,
            'success_rate': success_rate,
            'by_algorithm': by_algorithm,
            'by_interface': by_interface,
            'avg_execution_time_ms': avg_execution_time,
            'db_path': self.db_path
        }

    def close(self) -> None:
        """Close database connection (for cleanup)."""
        # SQLite connections are opened per-operation, no persistent connection
        pass


class PersistenceLogger:
    """
    High-level logging interface.

    Convenience wrapper around persistence backend that handles common
    logging patterns and data conversion.
    """

    def __init__(self, backend: Optional[AbstractPersistence] = None):
        """
        Initialize logger.

        Parameters:
        ----------
        backend : AbstractPersistence, optional
            Persistence backend. Uses SQLite if None.
        """
        self.backend = backend or SQLitePersistence()

    def log_transfer(
        self,
        run_id: str,
        source_hash: str,
        target_hash: str,
        result_hash: str,
        algorithm: str,
        config: Dict[str, Any],
        metrics: Dict[str, Any],
        interface_type: str,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log a transfer operation.

        Parameters:
        ----------
        run_id : str
            Unique run identifier
        source_hash : str
            SHA256 hash of source image
        target_hash : str
            SHA256 hash of target image
        result_hash : str
            SHA256 hash of result image
        algorithm : str
            Algorithm used
        config : Dict
            Configuration dictionary
        metrics : Dict
            Performance metrics dictionary
        interface_type : str
            Interface type (CLI, API, WebUI)
        success : bool
            Whether operation succeeded
        error_message : str, optional
            Error message if failed
        """
        run = TransferRun(
            run_id=run_id,
            timestamp=datetime.utcnow().isoformat(),
            source_hash=source_hash,
            target_hash=target_hash,
            result_hash=result_hash,
            algorithm=algorithm,
            config_json=json.dumps(config),
            metrics_json=json.dumps(metrics),
            interface_type=interface_type,
            success=success,
            error_message=error_message
        )

        self.backend.log_run(run)

    def get_history(
        self,
        limit: int = 100,
        algorithm: Optional[str] = None
    ) -> List[TransferRun]:
        """
        Get transfer history.

        Parameters:
        ----------
        limit : int
            Maximum number of entries
        algorithm : str, optional
            Filter by algorithm

        Returns:
        -------
        List[TransferRun]
            Recent transfer runs
        """
        return self.backend.list_runs(limit=limit, algorithm=algorithm)

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics."""
        return self.backend.get_statistics()
