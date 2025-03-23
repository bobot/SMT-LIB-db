#!/usr/bin/env python3

import sqlite3
import argparse
import sys
from pathlib import Path
from modules import benchmarks, evaluations

parser = argparse.ArgumentParser(
    prog="populate.py", description="Prepopulates the benchmark database."
)

parser.add_argument("DB_FILE", type=Path)
parser.add_argument("SMTCOMPWEB_FOLDER", type=Path)
parser.add_argument("SMTCOMP_FOLDER", type=Path)
parser.add_argument("SMTEVAL_CSV", type=Path)
parser.add_argument("SMTEXEC_DB", type=Path)
parser.add_argument("SMTCOMP_RAW", type=Path)
args = parser.parse_args()

connection = sqlite3.connect(args.DB_FILE)

benchmarks.calculate_benchmark_count(connection)
evaluations.add_smt_comps(
    connection,
    args.SMTCOMPWEB_FOLDER,
    args.SMTCOMP_FOLDER,
    args.SMTEVAL_CSV,
    args.SMTEXEC_DB,
)

connection.execute("create index evalIdx4 on SolverVariants(solver);")
connection.execute(
    "create index evalIdx5 on Results(query, solverVariant, status, evaluation);"
)
connection.execute("create index evalIdx6 on Evaluations(date);")

evaluations.add_eval_summaries(connection)

# Drop the indices such that we get a compact version.
connection.execute("drop index evalIdx4;")
connection.execute("drop index evalIdx5;")
connection.execute("drop index evalIdx6;")

connection.close()
