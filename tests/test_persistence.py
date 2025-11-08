"""
Tests for PersistenceLogger Module
==================================

Comprehensive tests for logging and database operations.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from color_transfer_framework.persistence_logger import (
    PersistenceLogger,
    SQLitePersistence,
    TransferRun
)


class TestSQLitePersistence:
    """Tests for SQLite persistence backend."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def persistence(self, temp_db):
        """Create SQLite persistence instance."""
        return SQLitePersistence(temp_db)

    def test_database_initialization(self, persistence, temp_db):
        """Test database and schema creation."""
        assert Path(temp_db).exists()

        # Verify tables exist
        import sqlite3
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert 'transfer_runs' in tables
        assert 'metadata' in tables

        conn.close()

    def test_log_run(self, persistence):
        """Test logging a transfer run."""
        run = TransferRun(
            run_id="test-123",
            timestamp=datetime.utcnow().isoformat(),
            source_hash="abc123",
            target_hash="def456",
            result_hash="ghi789",
            algorithm="reinhard_lab",
            config_json='{"blend_factor": 1.0}',
            metrics_json='{"execution_time_ms": 100.0}',
            interface_type="CLI",
            success=True
        )

        persistence.log_run(run)

        # Verify it was logged
        retrieved = persistence.get_run("test-123")
        assert retrieved is not None
        assert retrieved.run_id == "test-123"
        assert retrieved.algorithm == "reinhard_lab"
        assert retrieved.interface_type == "CLI"
        assert retrieved.success is True

    def test_log_run_with_error(self, persistence):
        """Test logging a failed run."""
        run = TransferRun(
            run_id="error-123",
            timestamp=datetime.utcnow().isoformat(),
            source_hash="abc123",
            target_hash="def456",
            result_hash="",
            algorithm="reinhard_lab",
            config_json='{}',
            metrics_json='{}',
            interface_type="API",
            success=False,
            error_message="Test error"
        )

        persistence.log_run(run)

        retrieved = persistence.get_run("error-123")
        assert retrieved is not None
        assert retrieved.success is False
        assert retrieved.error_message == "Test error"

    def test_get_nonexistent_run(self, persistence):
        """Test retrieving a run that doesn't exist."""
        result = persistence.get_run("nonexistent")
        assert result is None

    def test_list_runs(self, persistence):
        """Test listing recent runs."""
        # Log multiple runs
        for i in range(10):
            run = TransferRun(
                run_id=f"run-{i}",
                timestamp=datetime.utcnow().isoformat(),
                source_hash=f"src-{i}",
                target_hash=f"tgt-{i}",
                result_hash=f"res-{i}",
                algorithm="reinhard_lab" if i % 2 == 0 else "rgb_direct",
                config_json='{}',
                metrics_json='{}',
                interface_type="CLI" if i % 3 == 0 else "API",
                success=True
            )
            persistence.log_run(run)

        # List all
        runs = persistence.list_runs(limit=100)
        assert len(runs) == 10

        # List with limit
        runs = persistence.list_runs(limit=5)
        assert len(runs) == 5

        # Filter by algorithm
        runs = persistence.list_runs(algorithm="reinhard_lab")
        assert all(r.algorithm == "reinhard_lab" for r in runs)

        # Filter by interface
        runs = persistence.list_runs(interface_type="CLI")
        assert all(r.interface_type == "CLI" for r in runs)

    def test_get_statistics(self, persistence):
        """Test aggregate statistics."""
        # Log multiple runs
        for i in range(5):
            run = TransferRun(
                run_id=f"run-{i}",
                timestamp=datetime.utcnow().isoformat(),
                source_hash=f"src-{i}",
                target_hash=f"tgt-{i}",
                result_hash=f"res-{i}",
                algorithm="reinhard_lab",
                config_json='{}',
                metrics_json=json.dumps({"execution_time_ms": 100.0 * (i + 1)}),
                interface_type="CLI",
                success=True
            )
            persistence.log_run(run)

        stats = persistence.get_statistics()

        assert stats['total_runs'] == 5
        assert stats['success_rate'] == 100.0
        assert 'reinhard_lab' in stats['by_algorithm']
        assert stats['by_algorithm']['reinhard_lab'] == 5
        assert 'CLI' in stats['by_interface']
        assert stats['by_interface']['CLI'] == 5
        assert stats['avg_execution_time_ms'] == 300.0  # Average of 100, 200, 300, 400, 500

    def test_statistics_with_failures(self, persistence):
        """Test statistics with failed runs."""
        # Log successful run
        run1 = TransferRun(
            run_id="success-1",
            timestamp=datetime.utcnow().isoformat(),
            source_hash="abc",
            target_hash="def",
            result_hash="ghi",
            algorithm="reinhard_lab",
            config_json='{}',
            metrics_json='{"execution_time_ms": 100.0}',
            interface_type="CLI",
            success=True
        )
        persistence.log_run(run1)

        # Log failed run
        run2 = TransferRun(
            run_id="failure-1",
            timestamp=datetime.utcnow().isoformat(),
            source_hash="abc",
            target_hash="def",
            result_hash="",
            algorithm="reinhard_lab",
            config_json='{}',
            metrics_json='{}',
            interface_type="CLI",
            success=False,
            error_message="Test error"
        )
        persistence.log_run(run2)

        stats = persistence.get_statistics()
        assert stats['total_runs'] == 2
        assert stats['success_rate'] == 50.0


class TestPersistenceLogger:
    """Tests for high-level PersistenceLogger."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def logger(self, temp_db):
        """Create persistence logger instance."""
        backend = SQLitePersistence(temp_db)
        return PersistenceLogger(backend=backend)

    def test_log_transfer(self, logger):
        """Test logging a transfer operation."""
        logger.log_transfer(
            run_id="test-run-1",
            source_hash="abc123",
            target_hash="def456",
            result_hash="ghi789",
            algorithm="reinhard_lab",
            config={"blend_factor": 1.0, "algorithm": "reinhard_lab"},
            metrics={"execution_time_ms": 150.5, "memory_used_mb": 200.0},
            interface_type="CLI",
            success=True
        )

        # Verify it was logged
        run = logger.backend.get_run("test-run-1")
        assert run is not None
        assert run.algorithm == "reinhard_lab"
        assert run.success is True

        # Verify JSON serialization
        config = json.loads(run.config_json)
        assert config['blend_factor'] == 1.0

        metrics = json.loads(run.metrics_json)
        assert metrics['execution_time_ms'] == 150.5

    def test_log_transfer_with_error(self, logger):
        """Test logging a failed transfer."""
        logger.log_transfer(
            run_id="error-run-1",
            source_hash="abc123",
            target_hash="def456",
            result_hash="",
            algorithm="histogram_match",
            config={},
            metrics={},
            interface_type="API",
            success=False,
            error_message="Image dimensions mismatch"
        )

        run = logger.backend.get_run("error-run-1")
        assert run is not None
        assert run.success is False
        assert run.error_message == "Image dimensions mismatch"

    def test_get_history(self, logger):
        """Test retrieving transfer history."""
        # Log multiple transfers
        for i in range(15):
            logger.log_transfer(
                run_id=f"run-{i}",
                source_hash=f"src-{i}",
                target_hash=f"tgt-{i}",
                result_hash=f"res-{i}",
                algorithm="reinhard_lab" if i % 2 == 0 else "rgb_direct",
                config={},
                metrics={},
                interface_type="CLI"
            )

        # Get recent history
        history = logger.get_history(limit=10)
        assert len(history) == 10

        # Get filtered history
        history = logger.get_history(algorithm="reinhard_lab")
        assert all(r.algorithm == "reinhard_lab" for r in history)

    def test_get_stats(self, logger):
        """Test getting aggregate statistics."""
        # Log some transfers
        for i in range(3):
            logger.log_transfer(
                run_id=f"run-{i}",
                source_hash=f"src-{i}",
                target_hash=f"tgt-{i}",
                result_hash=f"res-{i}",
                algorithm="reinhard_lab",
                config={},
                metrics={"execution_time_ms": 100.0},
                interface_type="CLI"
            )

        stats = logger.get_stats()
        assert stats['total_runs'] == 3
        assert stats['success_rate'] == 100.0
        assert stats['avg_execution_time_ms'] == 100.0


class TestIntegration:
    """Integration tests for persistence layer."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)

    def test_multiple_interfaces(self, temp_db):
        """Test logging from multiple interfaces."""
        logger = PersistenceLogger(backend=SQLitePersistence(temp_db))

        # Log from different interfaces
        logger.log_transfer(
            run_id="cli-1", source_hash="a", target_hash="b", result_hash="c",
            algorithm="reinhard_lab", config={}, metrics={}, interface_type="CLI"
        )

        logger.log_transfer(
            run_id="api-1", source_hash="d", target_hash="e", result_hash="f",
            algorithm="rgb_direct", config={}, metrics={}, interface_type="API"
        )

        logger.log_transfer(
            run_id="webui-1", source_hash="g", target_hash="h", result_hash="i",
            algorithm="histogram_match", config={}, metrics={}, interface_type="WebUI"
        )

        # Verify all logged
        stats = logger.get_stats()
        assert stats['total_runs'] == 3
        assert len(stats['by_interface']) == 3
        assert stats['by_interface']['CLI'] == 1
        assert stats['by_interface']['API'] == 1
        assert stats['by_interface']['WebUI'] == 1

    def test_concurrent_logging(self, temp_db):
        """Test that concurrent writes work correctly."""
        logger = PersistenceLogger(backend=SQLitePersistence(temp_db))

        # Simulate rapid concurrent logging
        for i in range(50):
            logger.log_transfer(
                run_id=f"concurrent-{i}",
                source_hash=f"src-{i}",
                target_hash=f"tgt-{i}",
                result_hash=f"res-{i}",
                algorithm="reinhard_lab",
                config={},
                metrics={},
                interface_type="CLI"
            )

        # Verify all were logged
        stats = logger.get_stats()
        assert stats['total_runs'] == 50
