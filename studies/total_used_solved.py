#!/usr/bin/env python3

"""
Prints for each year:
  * num. of total benchmarks
  * num. of benchmarks that have appeared in an earlier competition
  * num. of benchmarks where a solver in an earlier competition returned "sat" or "unsat"
  -> non-incremental only
"""


import argparse
import sqlite3

parser = argparse.ArgumentParser()

parser.add_argument("database")
parser.add_argument("--logic", default="ALL")

args = parser.parse_args()

if args.logic == "ALL":
    args.logic = "%"

connection = sqlite3.connect(args.database)

years = list(range(2005, 2025))

print(f"Year; Benchmarks; Used; Solved")
for year in years:
    yearstr = f"{year}-12-31"
    oldyearstr = f"{year-1}-12-31"
    # Counts total number of benchmarks
    for row in connection.execute(
        """
        SELECT COUNT(bnch.id) FROM Benchmarks AS bnch
        JOIN Families AS fam ON fam.id = bnch.family
        WHERE NOT bnch.isIncremental
        AND fam.firstOccurrence <= ?
        AND bnch.logic LIKE ?;
        """,
        (yearstr, args.logic),
    ):
        total = row[0]
    # Counts benchark that have a first occurence before the current year
    for row in connection.execute(
        """
        SELECT count(DISTINCT bnch.id) FROM Benchmarks AS bnch
        JOIN Queries AS  qr ON qr.benchmark = bnch.id
        JOIN Results AS res ON res.query = qr.id
        JOIN Evaluations AS eval ON eval.id = res.evaluation
        WHERE NOT bnch.isIncremental
        AND eval.date <= ?
        AND bnch.logic LIKE ?;
        """,
        (oldyearstr, args.logic),
    ):
        used = row[0]
    # Counts benchark where there was a sat/unsat at some point before
    for row in connection.execute(
        """
        SELECT count(DISTINCT bnch.id) FROM Benchmarks AS bnch
        JOIN Queries AS qr  ON qr.benchmark = bnch.id
        JOIN Results AS res ON res.query = qr.id
        JOIN Evaluations as eval ON eval.id = res.evaluation
        WHERE NOT bnch.isIncremental
        AND eval.date <= ?
        AND (res.status == 'sat' OR res.status == 'unsat')
        AND bnch.logic LIKE ?;
        """,
        (oldyearstr, args.logic),
    ):
        solved = row[0]

    print(f"{year}; {total}; {used}; {solved}")

connection.close()
