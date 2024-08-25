#!/usr/bin/env python3

"""
Helper script to print mapping between solver clean name,
solver id, and Starexec name.
"""

import csv
import sys

smtdir = sys.argv[1]

idToName = dict()
with open(f"{smtdir}/registration/solvers_divisions_all.csv", newline="") as csvfile:
    solvers = csv.DictReader(csvfile, delimiter=",")
    for row in solvers:
        solverID = row["Config ID Single Query"]
        idToName[solverID] = row["Solver Name"]

idToStarexec = dict()
with open(f"{smtdir}/results/raw-results-sq.csv", newline="") as csvfile:
    reader = csv.DictReader(csvfile, delimiter=",")
    for row in reader:
        idToStarexec[row["configuration id"]] = row["solver"]

maxlen = max(map(len, idToName.values()))

for k in idToName:
    try:
        print(f"{k} {idToName[k]:>{maxlen}}\t{idToStarexec[k]}")
    except KeyError:
        pass
