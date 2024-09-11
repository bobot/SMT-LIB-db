#!/usr/bin/env bash

echo "Adding indices after adding benchmarks"
echo "    on file" "$1"

echo "Add index for Benchmarks table"
sqlite3 "$1" "create index benchIdx1 on Benchmarks(filename, family, logic, isIncremental);"

echo "Add index for Subbenchmarks table"
sqlite3 "$1" "create index benchIdx2 on Subbenchmarks(benchmark);"

echo "Add index for Families table"
sqlite3 "$1" "create index benchIdx3 on Families(name, folderName);"

echo "Call SQLite analyze."
sqlite3 "$1" "analyze;"
