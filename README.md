# Tooling to Build a Database of SMT-LIB Problems

This repository contains Python scripts that can be used to build a database
from a folder that contains a copy of the SMT-LIB benchmark library.  Such a
database can than be used to quickly select benchmarks for experiments, or to
study the benchmark library itself.

The database will also store results large-scale evaluations, such as 
SMT-COMP.  This will allow us to track benchmark difficulty over time.

For more information on the webapp and the database scheme see the
`README_RELEASE.md` file.

## Scripts

* `prepopulate.py` sets up the database file and inserts static data.
* `addbenchmark.py` adds a benchmark to the database file.
* `postprocess.py` adds evaluations, and performs any other operation that
  requires all benchmarks to be in the database.

## TODO
- Optimize for reading.  See for example here:
  https://jacobfilipp.com/sqliteoptimize/
