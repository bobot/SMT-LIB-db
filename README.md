# Tooling to Build a Database of SMT-LIB Problems

This repository contains Python scripts that can be used to build a database
from a folder that contains a copy of the SMT-LIB benchmark library.  Such a
database can than be used to quickly select benchmarks for experiments, or to
study the benchmark library itself.

The database will also store results large-scale evaluations, such as 
SMT-COMP.  This will allow us to track benchmark difficulty over time.

## Database Scheme

The scheme is not yet fixed, and can evolve as we implement features.
The SMT-LIB folder structure follows the scheme `[LOGIC]/[DATE]-[BENCHMARKSET]/[FILENAME]`.

```sql
-- One entry per benchmark file.
CREATE TABLE Benchmarks(
        id INTEGER PRIMARY KEY,
        filename TEXT NOT NULL,
        family INT,
        logic NVARCHAR(100) NOT NULL,
        isIncremental BOOL,
        size INT,
        compressedSize INT, -- Size, after compressing with a standard algo.
        license INT,
        generatedOn DATETTIME,
        generatedBy TEXT,
        generator TEXT,
        application TEXT,
        description TEXT,
        category TEXT,
        subbenchmarkCount INT NOT NULL,
        FOREIGN KEY(family) REFERENCES Families(id)
        FOREIGN KEY(license) REFERENCES Licenses(id)
    );
-- One per (check-sat) call.
CREATE TABLE Subbenchmarks(
        id INTEGER PRIMARY KEY,
        benchmark INT,
        normalizedSize INT,
        compressedSize INT,
        defineFunCount INT,
        maxTermDepth INT,
        numSexps INT,
        numPatterns INT,
        FOREIGN KEY(benchmark) REFERENCES Benchmarks(id)
    );
-- Benchmark sets
CREATE TABLE Families(
        id INTEGER PRIMARY KEY,
        name NVARCHAR(100) NOT NULL,
        folderName TEXT NOT NULL,
        date DATE,
        benchmarkCount INT NOT NULL,
        UNIQUE(folderName)
    );
-- Tables to store counts of things like interpreted constants, ite, let, etc.
CREATE TABLE SyntacticFeatures(
    id INTEGER PRIMARY KEY,
    name TEXT);
CREATE TABLE SyntacticFeatureCounts(
    feature INT,
    benchmark INT,
    count INT NOT NULL,
    FOREIGN KEY(feature) REFERENCES SyntacticFeatures(id)
    FOREIGN KEY(benchmark) REFERENCES Benchmarks(id)
);
-- One per license used by a benchmark
CREATE TABLE Licenses(
        id INTEGER PRIMARY KEY,
        name TEXT,
        link TEXT,
        spdxIdentifier TEXT);
-- Lists known solvers
CREATE TABLE Solvers(
        id INTEGER PRIMARY KEY,
        name TEXT,
        link TEXT);
-- Since solvers use different versioning schemes, there is
-- no proper version table.  Instead there is only one tables
-- that can be used both for versions, and multiple variants
-- submited to the same competition. 
CREATE TABLE SolverVariants(
        id INTEGER PRIMARY KEY,
        fullName TEXT,
        solver INT,
        FOREIGN KEY(solver) REFERENCES Solvers(id)
        );
-- Maps solvers to benchmarks
CREATE TABLE TargetSolvers(
    subbenchmark INT,
    solverVariant INT,
    FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
    FOREIGN KEY(solverVariant) REFERENCES SolverVaraiants(id)
    );

-- One entry per stored evaluation (typically SMT-COMPs)
CREATE TABLE Evaluations(
        id INTEGER PRIMARY KEY,
        name TEXT,
        date DATE,
        link TEXT
        );
-- The result of one experiment of an evaluation
CREATE TABLE Results(
        id INTEGER PRIMARY KEY,
        evaluation INTEGER,
        subbenchmark INT,
        solverVariant INT,
        cpuTime REAL,
        wallclockTime REAL,
        status TEXT,
        FOREIGN KEY(evaluation) REFERENCES Evaluations(id)
        FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
        FOREIGN KEY(solverVariant) REFERENCES SolverVaraiants(id)
        );
-- Dificulty ratings (see below)
CREATE TABLE Ratings(
        id INTEGER PRIMARY KEY,
        subbenchmark INT,
        evaluation INT,
        rating REAL,
        consideredSolvers INT,
        successfulSolvers INT,
        FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
        FOREIGN KEY(evaluation) REFERENCES Evaluations(id)
        );
```

Benchmark difficulty ratings are calculated for each evaluation.  This
calculation first counts the number $n$ of solvers that solved at least one
benchmark in the logic of the benchmark.  Then it count the number $m$ of
solvers that solved the benchmark.  The rating is $1 - m/n$.

## Scripts

* `prepopulate.py` sets up the database file and inserts static data.
* `addbenchmark.py` adds a benchmark to the database file.
* `postprocess.py` adds evaluations, and performs any other operation that
  requires all benchmarks to be in the database.

## Implemented

* Add benchmarks, and single sub-benchmark for non-incremental benchmarks.
* Add all licenses (hard coded).
* Add SMT-COMP 2022 results.

## TODO

* Support for incremental benchmarks.
* Parse metadata header.
* Support more SMT-COMPs.
* Refined difficulty rating. 
