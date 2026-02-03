import csv
import logging
from pathlib import Path
from typing import Generator, Dict, Any, Optional

class CsvReader:
    """
    Handles reading of CSV files with validation and streaming support.
    """
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.logger = logging.getLogger("migration.reader")

    def validate(self) -> None:
        """Validates that the file exists and is a file."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.file_path}")
        if not self.file_path.is_file():
            raise IsADirectoryError(f"Path is not a file: {self.file_path}")
        self.logger.debug(f"File validated: {self.file_path}")

    def count_rows(self) -> int:
        """Counts the total number of non-empty rows in the CSV."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return sum(1 for row in reader if any(row.values()))
        except Exception as e:
            self.logger.error(f"Error counting rows: {e}")
            return 0

    def read(self) -> Generator[Dict[str, Any], None, None]:
        """
        Yields rows from the CSV file as dictionaries.
        Skips empty rows.
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader, 1):
                    if not any(row.values()):
                        continue
                    yield row
        except Exception as e:
            self.logger.error(f"Error reading CSV: {e}")
            raise
