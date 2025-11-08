"""
History Exporter
================

Export and import run history for backup and portability.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class HistoryExporter:
    """Export and import transfer operation history."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path.home() / '.color_transfer' / 'persistence' / 'runs.db'
        self.db_path = Path(db_path)

    def export_to_json(self, output_path: str, limit: Optional[int] = None) -> int:
        """Export history to JSON file."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT * FROM runs ORDER BY timestamp DESC"
            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query)
            rows = cursor.fetchall()

            columns = [desc[0] for desc in cursor.description]
            data = [dict(zip(columns, row)) for row in rows]

            with open(output_path, 'w') as f:
                json.dump({
                    'exported_at': datetime.now().isoformat(),
                    'total_runs': len(data),
                    'runs': data
                }, f, indent=2)

            conn.close()
            logger.info(f"Exported {len(data)} runs to {output_path}")
            return len(data)

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return 0

    def export_to_csv(self, output_path: str, limit: Optional[int] = None) -> int:
        """Export history to CSV file."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = "SELECT * FROM runs ORDER BY timestamp DESC"
            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(rows)

            conn.close()
            logger.info(f"Exported {len(rows)} runs to {output_path}")
            return len(rows)

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return 0

    def import_from_json(self, input_path: str) -> int:
        """Import history from JSON file."""
        try:
            with open(input_path, 'r') as f:
                data = json.load(f)

            runs = data.get('runs', [])

            # TODO: Implement actual database import
            logger.info(f"Would import {len(runs)} runs from {input_path}")
            return len(runs)

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return 0

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of run history."""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM runs")
            total = cursor.fetchone()[0]

            cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM runs")
            first, last = cursor.fetchone()

            conn.close()

            return {
                'total_runs': total,
                'first_run': first,
                'last_run': last,
                'database_path': str(self.db_path)
            }

        except Exception as e:
            logger.error(f"Failed to get summary: {e}")
            return {'total_runs': 0}
