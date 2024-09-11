#!/usr/bin/env bash

echo "Adding indices after adding evaluations"
echo "    on file" "$1"

echo "Add index for Symbols table"
sqlite3 "$1" "create index evalIdx1 on Symbols(name);"

echo "Add index for SymbolsCounts table"
sqlite3 "$1" "create index evalIdx2 on SymbolsCounts(symbol, subbenchmark, count);"

echo "Add index for SolverVariants table"
sqlite3 "$1" "create index evalIdx4 on SolverVariants(solver);"

echo "Add index for Results table"
sqlite3 "$1" "create index evalIdx5 on Results(subbenchmark, solverVariant);"

echo "Call SQLite analyze."
sqlite3 "$1" "analyze;"
