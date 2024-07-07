#!/usr/bin/env python3

import sqlite3
import argparse
from pathlib import Path
from modules import benchmarks, evaluations

parser = argparse.ArgumentParser(
    prog="populate.py", description="Prepopulates the benchmark database."
)

parser.add_argument("DB_FILE", type=Path)
parser.add_argument("SMTCOMPWEB_FOLDER", type=Path)
parser.add_argument("SMTCOMP_FOLDER", type=Path)
args = parser.parse_args()

connection = sqlite3.connect(args.DB_FILE)

benchmarks.calculate_benchmark_count(connection)
evaluations.add_smt_comps(connection, args.SMTCOMPWEB_FOLDER, args.SMTCOMP_FOLDER)
evaluations.add_ratings(connection)

connection.close()
