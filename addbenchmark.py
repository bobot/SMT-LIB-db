#!/usr/bin/env python3

import sqlite3
import argparse
from pathlib import Path
from modules import benchmarks

parser = argparse.ArgumentParser(
    prog="addbenchmark.py", description="Adds a benchmark to the database."
)

parser.add_argument("DB_FILE", type=Path)
parser.add_argument("DOLMEN_BIN", type=Path)
parser.add_argument("BENCHMARK", type=Path)
args = parser.parse_args()

if not args.BENCHMARK.exists():
    raise Exception("Benchmark file does not exist.")

benchmarks.add_benchmark(args.DB_FILE, args.BENCHMARK, args.DOLMEN_BIN)
