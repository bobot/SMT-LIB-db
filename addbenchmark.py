#!/usr/bin/env python3

import sqlite3
import argparse
from pathlib import Path
from modules import benchmarks

parser = argparse.ArgumentParser(
    prog="addbenchmark.py", description="Adds a benchmark to the database."
)

parser.add_argument("DB_FILE", type=Path)
parser.add_argument("BENCHMARK", type=Path)
args = parser.parse_args()

if not args.BENCHMARK.exists():
    raise Exception("Benchmark file does not exist.")

connection = sqlite3.connect(args.DB_FILE, timeout=30.0)
# This should not be necessary, because WAL mode is persistent, but we
# add it here to be sure.
connection.execute("PRAGMA journal_mode=wal")

benchmarks.add_benchmark(connection, args.BENCHMARK)
connection.close()
