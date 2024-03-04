#!/usr/bin/env python3

import sqlite3
import argparse
from pathlib import Path
from modules import licenses, benchmarks, evaluations, solvers

parser = argparse.ArgumentParser(
    prog="prepopulate.py", description="Prepopulates the benchmark database."
)

parser.add_argument("DB_FILE", type=Path)
args = parser.parse_args()

connection = sqlite3.connect(args.DB_FILE)

connection.execute("PRAGMA foreign_keys = ON;")
connection.execute('PRAGMA journal_mode=wal')

connection.execute(
    """CREATE TABLE TargetSolvers(
    benchmark INT,
    solverVariant INT,
    FOREIGN KEY(benchmark) REFERENCES Benchmarks(id)
    FOREIGN KEY(solverVariant) REFERENCES SolverVaraiants(id)
    );"""
)

connection.commit()

licenses.setup_licenses(connection)
benchmarks.setup_benchmarks(connection)
evaluations.setup_evaluations(connection)
solvers.setup_solvers(connection)
connection.close()
