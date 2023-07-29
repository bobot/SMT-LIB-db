#!/usr/bin/env python3

import sqlite3
import argparse
from pathlib import Path
from modules import licenses, benchmarks, evaluations

parser = argparse.ArgumentParser(
    prog="prepopulate.py", description="Prepopulates the benchmark database."
)

parser.add_argument("DB_FILE", type=Path)
args = parser.parse_args()

connection = sqlite3.connect(args.DB_FILE)

connection.execute("PRAGMA foreign_keys = ON;")

connection.execute(
    """CREATE TABLE SyntacticFeatures(
    id INTEGER PRIMARY KEY,
    name TEXT);"""
)

connection.execute(
    """CREATE TABLE SyntacticFeatureCounts(
    feature INT,
    benchmark INT,
    count INT NOT NULL,
    FOREIGN KEY(feature) REFERENCES SyntacticFeatures(id)
    FOREIGN KEY(benchmark) REFERENCES Benchmarks(id)
);"""
)

connection.execute(
    """CREATE TABLE TargetSolvers(
    subbenchmark INT,
    solverVariant INT,
    FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
    FOREIGN KEY(solverVariant) REFERENCES SolverVaraiants(id)
    );"""
)

# TODO: add evaluation table, fix solvers table

connection.execute(
    """CREATE TABLE Results(
    id INTEGER PRIMARY KEY,
    subbenchmark INT,
    solver INT,
    solvingTime REAL,
    status TEXT,
    FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
    FOREIGN KEY(solver) REFERENCES Subbenchmarks(id)
);"""
)

connection.execute(
    """CREATE TABLE Ratings(
    id INTEGER PRIMARY KEY,
    subbenchmark INT,
    evaluation INT,
    rating REAL,
    FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
    FOREIGN KEY(evaluation) REFERENCES Evaluations(id)
);"""
)
connection.commit()

licenses.setup_licenses(connection)
benchmarks.setup_benchmarks(connection)
evaluations.setup_evaluations(connection)
connection.close()
