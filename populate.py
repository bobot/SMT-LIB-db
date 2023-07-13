#!/usr/bin/env python3

import sqlite3

con = sqlite3.connect("smtlib.db")
cur = con.cursor()

cur.execute("PRAGMA foreign_keys = ON;")
cur.execute("""CREATE TABLE Sets(
    id INT NOT NULL PRIMARY KEY,
    logic NVARCHAR(100) NOT NULL,
    name NVARCHAR(100) NOT NULL,
    date DATE,
    isIncremental BOOL NOT NULL,
    benchmarkCount INT NOT NULL
);""")

cur.execute("""CREATE TABLE Benchmarks(
    id INT NOT NULL PRIMARY KEY,
    filename TEXT NOT NULL,
    benchmarkSet INT,
    setIndex INT NOT NULL,
    size INT,
    compressedSize INT,
    license INT,
    generatedOn DATETTIME,
    generatedBy TEXT,
    generator TEXT,
    application TEXT,
    description TEXT,
    category TEXT,
    subbenchmarkCount INT NOT NULL,
    FOREIGN KEY(benchmarkSet) REFERENCES Sets(id)
    FOREIGN KEY(license) REFERENCES Licenses(id)
);""")

cur.execute("""CREATE TABLE Subbenchmarks(
    id INT NOT NULL PRIMARY KEY,
    benchmark INT,
    normalizedSize INT,
    compressedSize INT,
    defineFunCount INT,
    maxTermDepth INT,
    numSexps INT,
    numPatterns INT,
    FOREIGN KEY(benchmark) REFERENCES Benchmarks(id)
);""")

cur.execute("""CREATE TABLE SyntacticFeatures(
    id INT NOT NULL PRIMARY KEY,
    name TEXT);""")

cur.execute("""CREATE TABLE SyntcticFeatureCounts(
    feature INT,
    benchmark INT,
    count INT NOT NULL,
    FOREIGN KEY(feature) REFERENCES SyntacticFeatures(id)
    FOREIGN KEY(benchmark) REFERENCES Benchmarks(id)
);""")

cur.execute("""CREATE TABLE Solvers(
    id INT NOT NULL PRIMARY KEY,
    name TEXT,
    version TEXT,
    link TEXT);""")

cur.execute("""CREATE TABLE TargetSolvers(
    subbenchmark INT,
    solver INT,
    FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
    FOREIGN KEY(solver) REFERENCES Solvers(id)
    );""")

cur.execute("""CREATE TABLE Results(
    id INT NOT NULL PRIMARY KEY,
    subbenchmark INT,
    solver INT,
    solvingTime REAL,
    status TEXT,
    FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
    FOREIGN KEY(solver) REFERENCES Subbenchmarks(id)
);""")

cur.execute("""CREATE TABLE Ratings(
    id INT NOT NULL PRIMARY KEY,
    subbenchmark INT,
    evaluation INT,
    rating REAL,
    FOREIGN KEY(subbenchmark) REFERENCES Subbenchmarks(id)
    FOREIGN KEY(evaluation) REFERENCES Evaluations(id)
);""")

cur.execute("""CREATE TABLE Licenses(
    id INT NOT NULL PRIMARY KEY,
    name TEXT,
    shortCode TEXT,
    link TEXT,
    spdxIdentifier TEXT
);""")


