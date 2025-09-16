#!/usr/bin/env python3

import argparse
import sqlite3
import statistics

"""
    Prints the number of solvers that participated in each evaluation
    (per logic).
"""


parser = argparse.ArgumentParser()

parser.add_argument("database")

args = parser.parse_args()

connection = sqlite3.connect(args.database)

years = list(range(2005, 2025))

res = connection.execute("SELECT DISTINCT logic FROM Benchmarks")
logics = res.fetchall()

res = connection.execute("SELECT id,name,date FROM Evaluations")
evaluations = res.fetchall()

print("Date;Evaluation", end="")
for (logic,) in logics:
    print(f";{logic}", end="")
print("")

for evalId, evalName, evalDate in evaluations:
    print(f"{evalDate};{evalName}", end="")
    for (logic,) in logics:
        for logicSolversRow in connection.execute(
            """
            SELECT COUNT(DISTINCT s.id) FROM Solvers AS s
                INNER JOIN SolverVariants AS sv ON sv.solver = s.id
                INNER JOIN Results AS r ON sv.id = r.solverVariant
                INNER JOIN Benchmarks AS b ON b.id = r.query
            WHERE b.logic=? AND r.evaluation=? AND b.isIncremental=0
            """,
            (logic, evalId),
        ):
            print(f";{logicSolversRow[0]}", end="")
    print("")
