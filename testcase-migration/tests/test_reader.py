import unittest
import os
import tempfile
from pathlib import Path
from src.core.reader import CsvReader

class TestCsvReader(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.test_dir.name) / "test.csv"
        with open(self.csv_path, "w", encoding="utf-8") as f:
            f.write("ID,Title\n1,Test 1\n2,Test 2\n")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_count_rows(self):
        reader = CsvReader(str(self.csv_path))
        self.assertEqual(reader.count_rows(), 2)

    def test_read_integration(self):
        reader = CsvReader(str(self.csv_path))
        rows = list(reader.read())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['Title'], "Test 1")

if __name__ == '__main__':
    unittest.main()
