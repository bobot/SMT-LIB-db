#!/usr/bin/env python3

import sqlite3
import argparse
from pathlib import Path
from modules import licenses, benchmarks, evaluations, solvers, logics

parser = argparse.ArgumentParser(
    prog="prepopulate.py", description="Prepopulates the benchmark database."
)

parser.add_argument("DB_FILE", type=Path)
args = parser.parse_args()

connection = sqlite3.connect(args.DB_FILE)

connection.execute("PRAGMA foreign_keys = ON;")
connection.execute("PRAGMA journal_mode=wal")
connection.commit()

licenses.setup_licenses(connection)
evaluations.setup_evaluations(connection)
solvers.setup_solvers(connection)
benchmarks.setup_benchmarks(connection)
logics.setup_logics(connection)
logics.write_all_logics(connection)
connection.close()
