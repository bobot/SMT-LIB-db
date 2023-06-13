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
    benchmarkSet INT FOREIGN KEY REFERENCES Sets(id)
    setIndex INT NOT NULL,
    size INT,
    compressedSize INT,
    license INT FOREIGN KEY REFERENCES Licenses(id)
    generatedOn DATETTIME,
    generatedBy TEXT,
    generator TEXT,
    application TEXT,
    description TEXT,
    category TEXT,
    subbenchmarkCount INT NOT NULL
);""")

cur.execute("""CREATE TABLE Subbenchmarks(
    id INT NOT NULL PRIMARY KEY,
    benchmark INT FOREIGN KEY REFERENCES Benchmarks(id)
    normalizedSize INT,
    compressedSize INT,
    defineFunCount INT,
    maxTermDepth INT,
    numSexps INT,
    numPatterns INT
);""")

cur.execute("""CREATE TABLE SyntcticFeatures(
    id INT NOT NULL PRIMARY KEY,
    name TEXT);""")

cur.execute("""CREATE TABLE SyntcticalFeatureCounts(
    feature INT FOREIGN KEY REFERENCES SyntcticFeatures(id),
    benchmark INT FOREIGN KEY REFERENCES Benchmarks(id),
    count INT NOT NULL);""")

cur.execute("""CREATE TABLE Solvers(
    id INT NOT NULL PRIMARY KEY,
    name TEXT,
    version TEXT,
    link TEXT);""")

cur.execute("""CREATE TABLE TargetSolvers(
    subbenchmark INT FOREIGN KEY REFERENCES Subbenchmarks(id),
    solver INT FOREIGN KEY REFERENCES Solvers(id)
    );""")

cur.execute("""CREATE TABLE Results(
    id INT NOT NULL PRIMARY KEY,
    subbenchmark INT FOREIGN KEY REFERENCES Subbenchmarks(id),
    solver INT FOREIGN KEY REFERENCES Solvers(id),
    solved BOOL);""")

cur.execute("""CREATE TABLE Ratings(
    id INT NOT NULL PRIMARY KEY,
    subbenchmark INT FOREIGN KEY REFERENCES Subbenchmarks(id),
    evaluation INT FOREIGN KEY REFERENCES Evaluations(id),
    rating REAL);""")

cur.execute("""CREATE TABLE Licenses(
    id INT NOT NULL PRIMARY KEY,
    name TEXT,
    shortCode TEXT,
    link TEXT,
    spdxIdentifier TEXT);""")


