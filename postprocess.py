#!/usr/bin/env python3

import sqlite3
import argparse
from pathlib import Path
from modules import benchmarks

parser = argparse.ArgumentParser(
    prog="populate.py", description="Prepopulates the benchmark database."
)

parser.add_argument("DB_FILE", type=Path)
args = parser.parse_args()

connection = sqlite3.connect(args.DB_FILE)

benchmarks.calculate_benchmark_count(connection)
connection.close()
